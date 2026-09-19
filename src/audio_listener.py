"""
Real-Time Internal System Audio (WASAPI Loopback) & Microphone Speech-to-Text Translation.
Directly captures YouTube, PC Games, Video Players, and Streams audio and translates in real-time.

Supports two modes:
1. Gemini Direct Audio (fast) — sends audio WAV directly to Gemini for STT+Translation in one call
2. Google STT + Translate (fallback) — uses Google Web Speech API then translates separately
"""
import io
import os
import time
import numpy as np
import soundfile as sf
import speech_recognition as sr
from typing import Optional, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal

try:
    import pyaudiowpatch as pyaudio
    HAS_PYAUDIO = True
except ImportError:
    import pyaudio
    HAS_PYAUDIO = True

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

from src.translator import TranslationEngine
from src.utils import ConfigManager, clean_ocr_text


class AudioTranslatorWorker(QThread):
    """
    Background worker that captures Internal PC Audio (YouTube, Games, Discord) via WASAPI Loopback
    or Microphone, detects speech, and translates to Thai subtitles in real-time.
    
    Uses Gemini Direct Audio mode when available for maximum speed and accuracy.
    """
    new_subtitles = pyqtSignal(str, str)  # (thai_text, original_speech_text)
    speech_detected = pyqtSignal(str)     # (original_speech_text)
    audio_status = pyqtSignal(str, str)   # (status_message, color_hex)
    audio_level = pyqtSignal(int)         # (0-100 volume meter)

    def __init__(self, config_mgr: ConfigManager):
        super().__init__()
        self.config_mgr = config_mgr
        self.config = self.config_mgr.config
        
        self.translator = TranslationEngine(self.config.get("translation", {}))
        self.recognizer = sr.Recognizer()
        
        self._is_running = False
        self._is_paused = False
        self._audio_mode = self.config.get("audio", {}).get("mode", "loopback")  # "loopback" or "mic"
        
        # Gemini client for direct audio processing
        self._gemini_client = None
        self._init_gemini_client()
        
        # Audio Processing parameters
        self.silence_threshold = 200  # Lower threshold for better sensitivity
        self._audio_buffer = []
        self._voice_active = False
        self._silence_chunks = 0
        self._last_speech = ""

    def _init_gemini_client(self):
        """Initializes Gemini client for direct audio transcription+translation."""
        if not HAS_GENAI:
            return
        trans_cfg = self.config.get("translation", {})
        gemini_key = trans_cfg.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
        if gemini_key:
            try:
                self._gemini_client = genai.Client(api_key=gemini_key)
                print("[AudioTranslator] Gemini Direct Audio mode enabled (fast)")
            except Exception as e:
                print(f"[AudioTranslator] Gemini client init warning: {e}")

    def _can_use_gemini_audio(self) -> bool:
        """Checks if Gemini direct audio mode is available."""
        trans_cfg = self.config.get("translation", {})
        engine = trans_cfg.get("engine", "auto")
        has_key = bool(trans_cfg.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", ""))
        return HAS_GENAI and has_key and engine == "gemini" and self._gemini_client is not None

    def update_settings(self):
        """Reloads settings from config."""
        self.config = self.config_mgr.config
        self.translator.update_config(self.config.get("translation", {}))
        self._audio_mode = self.config.get("audio", {}).get("mode", "loopback")
        # Re-init Gemini if key changed
        self._init_gemini_client()

    def set_audio_mode(self, mode: str):
        """Switches between 'loopback' (internal PC sound) and 'mic' (microphone)."""
        self._audio_mode = mode
        self.config.setdefault("audio", {})["mode"] = mode
        self.config_mgr.save_config(self.config)

    def start_worker(self):
        """Starts the audio listening thread."""
        self._is_running = True
        self._is_paused = False
        if not self.isRunning():
            self.start()

    def pause_worker(self):
        """Pauses audio listening."""
        self._is_paused = True
        self.audio_status.emit("⏸️ ระบบแปลเสียงหยุดชั่วคราว", "#FFAA00")

    def resume_worker(self):
        """Resumes audio listening."""
        self._is_paused = False
        self.audio_status.emit("🔊 กำลังดักฟังเสียงภายในคอม / เกม / YouTube...", "#00FFCC")

    def toggle_pause(self) -> bool:
        if self._is_paused:
            self.resume_worker()
            return False
        else:
            self.pause_worker()
            return True

    def stop_worker(self):
        """Stops the audio thread."""
        self._is_running = False
        self.wait(1000)

    def _get_loopback_device(self, p: pyaudio.PyAudio):
        """Finds default WASAPI loopback device for capturing internal computer audio."""
        try:
            wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
            default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
            
            if not default_speakers.get("isLoopbackDevice", False):
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        return loopback
                for loopback in p.get_loopback_device_info_generator():
                    return loopback
            return default_speakers
        except Exception as e:
            print(f"[AudioTranslatorWorker] WASAPI loopback lookup warning: {e}")
            return None

    def run(self):
        """Main audio capture and STT processing loop."""
        mode_text = "🎙️ ไมโครโฟน" if self._audio_mode == "mic" else "🔊 เสียงในคอม"
        method = "Gemini Direct" if self._can_use_gemini_audio() else "Google STT"
        self.audio_status.emit(f"{mode_text} ({method})...", "#00FFCC")

        p = pyaudio.PyAudio()
        stream = None

        try:
            device_info = None
            if self._audio_mode == "loopback":
                device_info = self._get_loopback_device(p)

            if device_info is None:
                # Fallback to default input
                device_info = p.get_default_input_device_info()

            dev_index = int(device_info["index"])
            rate = int(device_info.get("defaultSampleRate", 48000))
            channels = int(device_info.get("maxInputChannels", 2))
            frames_per_buffer = 2048

            stream = p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=rate,
                input=True,
                input_device_index=dev_index,
                frames_per_buffer=frames_per_buffer
            )

            chunk_time = frames_per_buffer / rate

            while self._is_running:
                if self._is_paused:
                    self.msleep(150)
                    continue

                try:
                    data = stream.read(frames_per_buffer, exception_on_overflow=False)
                except Exception:
                    continue

                if not data or not self._is_running:
                    break

                # Convert to numpy array
                chunk_arr = np.frombuffer(data, dtype=np.int16)
                if channels == 2:
                    chunk_arr = chunk_arr.reshape(-1, 2).mean(axis=1).astype(np.int16)

                # Volume level (RMS)
                rms = int(np.sqrt(np.mean(chunk_arr.astype(np.float32)**2)))
                volume_percent = min(100, int((rms / 2500) * 100))
                self.audio_level.emit(volume_percent)

                # Voice Activity Detection
                if rms > self.silence_threshold:
                    self._voice_active = True
                    self._silence_chunks = 0
                    self._audio_buffer.append(chunk_arr)
                    if len(self._audio_buffer) <= 2:
                        self.audio_status.emit("🔊 ได้ยินเสียงพูด...", "#00FFCC")
                else:
                    if self._voice_active:
                        self._audio_buffer.append(chunk_arr)
                        self._silence_chunks += 1

                        # Faster silence detection: ~0.5 second
                        chunks_for_silence = max(2, int(0.5 / chunk_time))
                        if self._silence_chunks >= chunks_for_silence and len(self._audio_buffer) >= 3:
                            self._process_speech_buffer(rate)
                            self._audio_buffer = []
                            self._voice_active = False
                            self._silence_chunks = 0

                # Prevent buffer overflow — max 6 seconds of continuous speech
                max_chunks = int(6.0 / chunk_time)
                if len(self._audio_buffer) > max_chunks:
                    self._process_speech_buffer(rate)
                    self._audio_buffer = []
                    self._voice_active = False
                    self._silence_chunks = 0

        except Exception as e:
            print(f"[AudioTranslatorWorker] Audio Loop Exception: {e}")
            self.audio_status.emit(f"⚠️ Audio Error: {e}", "#FF4444")
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            p.terminate()

    def _process_speech_buffer(self, rate: int):
        """Converts audio chunk buffer to text and translates."""
        if not self._audio_buffer:
            return

        try:
            full_audio = np.concatenate(self._audio_buffer, axis=0)
            wav_io = io.BytesIO()
            sf.write(wav_io, full_audio, rate, format="WAV")
            wav_bytes = wav_io.getvalue()

            self.audio_status.emit("⚡ กำลังแปลเสียง...", "#FFFF00")

            # Try Gemini Direct Audio first (1 API call = STT + Translation)
            if self._can_use_gemini_audio():
                result = self._translate_audio_gemini(wav_bytes)
                if result:
                    thai_text, original_text = result
                    if thai_text and thai_text != self._last_speech:
                        self._last_speech = thai_text
                        display_original = original_text if original_text else "🔊 (audio)"
                        self.new_subtitles.emit(thai_text, f"🔊 {display_original}")
                        self.audio_status.emit("✅ แปลเสียงสำเร็จ (Gemini)", "#00FFCC")
                    return

            # Fallback: Google STT → Translate (2 API calls)
            self._translate_audio_google_stt(wav_bytes, rate)

        except Exception as e:
            print(f"[AudioTranslatorWorker] Speech processing error: {e}")

    def _translate_audio_gemini(self, wav_bytes: bytes) -> Optional[tuple]:
        """
        Sends audio WAV directly to Gemini for transcription + translation in ONE API call.
        Returns (thai_text, original_text) or None on failure.
        """
        try:
            trans_cfg = self.config.get("translation", {})
            model_name = trans_cfg.get("gemini_model", "gemini-3.6-flash")
            target_lang = trans_cfg.get("target_lang", "th")
            source_lang = trans_cfg.get("source_lang", "auto")
            
            lang_names = {"th": "ภาษาไทย", "en": "English", "ja": "日本語", "zh": "中文", "ko": "한국어"}
            target_name = lang_names.get(target_lang, "Thai")
            
            source_hint = ""
            if source_lang != "auto":
                source_name = lang_names.get(source_lang, source_lang)
                source_hint = f"The speech is in {source_name}. "

            prompt = (
                f"Listen to this audio carefully. {source_hint}"
                f"Do two things:\n"
                f"1. Transcribe what was spoken.\n"
                f"2. Translate it into natural, conversational {target_name}.\n\n"
                f"Output format (exactly 2 lines, nothing else):\n"
                f"ORIGINAL: <transcribed text>\n"
                f"TRANSLATED: <translated text>\n\n"
                f"Rules:\n"
                f"- If no clear speech is detected, output nothing.\n"
                f"- Use natural spoken style, not formal.\n"
                f"- Keep names and proper nouns as-is.\n"
                f"- Ignore background music, sound effects, and noise."
            )

            response = self._gemini_client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav"),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=500
                )
            )

            if not response or not response.text:
                return None

            text = response.text.strip()
            
            # Parse the 2-line format
            original = ""
            translated = ""
            for line in text.split("\n"):
                line = line.strip()
                if line.upper().startswith("ORIGINAL:"):
                    original = line[len("ORIGINAL:"):].strip()
                elif line.upper().startswith("TRANSLATED:"):
                    translated = line[len("TRANSLATED:"):].strip()

            # If parsing failed, use the whole response as translation
            if not translated and text:
                translated = text
            
            # Remove wrapping quotes
            for s in [original, translated]:
                if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
                    s = s[1:-1]

            if translated and len(translated) >= 2:
                return (translated, original)
            return None

        except Exception as e:
            print(f"[AudioTranslator] Gemini Direct Audio error: {e}")
            return None

    def _translate_audio_google_stt(self, wav_bytes: bytes, rate: int):
        """Fallback: Uses Google Web STT for transcription, then translates separately."""
        try:
            wav_io = io.BytesIO(wav_bytes)
            with sr.AudioFile(wav_io) as source:
                audio_data = self.recognizer.record(source)

            src_lang = self.config.get("translation", {}).get("source_lang", "auto")
            stt_lang = "en-US"
            if src_lang == "ja":
                stt_lang = "ja-JP"
            elif src_lang == "zh":
                stt_lang = "zh-CN"
            elif src_lang == "ko":
                stt_lang = "ko-KR"

            spoken_text = self.recognizer.recognize_google(audio_data, language=stt_lang)
            clean_speech = clean_ocr_text(spoken_text)

            if clean_speech and len(clean_speech) >= 2:
                if clean_speech.lower() != self._last_speech.lower():
                    self._last_speech = clean_speech
                    self.speech_detected.emit(f"🔊 {clean_speech}")
                    self.audio_status.emit("⚡ กำลังแปล...", "#FFFF00")

                    thai_text = self.translator.translate(clean_speech)
                    if thai_text:
                        self.new_subtitles.emit(thai_text, f"🔊 {clean_speech}")
                        self.audio_status.emit("✅ แปลเสียงสำเร็จ (STT)", "#00FFCC")

        except sr.UnknownValueError:
            pass
        except Exception as e:
            print(f"[AudioTranslator] Google STT error: {e}")
