#!/usr/bin/env python3
"""
live_translate_windows.py

Real-time audio transcription and translation for Windows.
- Audio capture via WASAPI Loopback (YouTube, PC Games, Videos) or Microphone / Sounddevice
- Speech-to-Text via faster-whisper (CTranslate2, local offline AI)
- Translation via Google Gemini AI, Ollama LLM, or TranslatePy
- UI: Floating translucent dark overlay (Tkinter) with side-by-side original + translation
"""

import argparse
import contextlib
import json
import os
import queue
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Optional, Tuple, List, cast

import numpy as np

# sounddevice for microphone input
try:
    import sounddevice as sd
    HAS_SD = True
except ImportError:
    HAS_SD = False

# pyaudiowpatch for WASAPI Loopback (system audio)
try:
    import pyaudiowpatch as pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

from live_translation.text_pipeline import (
    LANG_MENU,
    WAITING_ORIGINAL,
    WAITING_TRANSLATION,
    dedup_words_by_time,
    language_label,
    merge_overlap_text,
    punctuated_context,
    sentence_case_text,
    strip_hallucinations,
    take_blocks_for_translation,
    take_endpoint_blocks,
)
from live_translation.translators import (
    LanguageSettings,
    OllamaTranslator,
    GeminiTranslator,
    FallbackTranslator,
)

WHISPER_MODELS = ["tiny", "base", "small", "medium", "turbo", "large-v3"]


def load_config():
    """Loads config.json if present in the current or parent directory."""
    for p in ["config.json", os.path.join(os.path.dirname(__file__), "config.json")]:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return {}


def is_device_openable(device_idx: int) -> Tuple[bool, int]:
    """Test if a device can actually be opened by PortAudio, and return (openable, native_samplerate)."""
    if not HAS_SD:
        return False, 0
    try:
        dev = cast(dict, sd.query_devices(device_idx))
        if dev.get("max_input_channels", 0) <= 0:
            return False, 0
        hostapi = dev.get("hostapi", -1)
        api_name = sd.query_hostapis(hostapi).get("name", "") if hostapi >= 0 else ""
        if "wdm-ks" in api_name.lower():
            return False, 0
        
        native_sr = int(dev.get("default_samplerate", 16000)) or 16000
        with sd.InputStream(device=device_idx, channels=1, samplerate=native_sr):
            pass
        return True, native_sr
    except Exception:
        try:
            with sd.InputStream(device=device_idx, channels=1, samplerate=16000):
                pass
            return True, 16000
        except Exception:
            return False, 0


def list_devices():
    """Print all available audio devices on Windows and indicate working ones."""
    print("\n--- Available Audio Devices on Windows ---")
    if HAS_PYAUDIO:
        try:
            p = pyaudio.PyAudio()
            print("  [Loopback Available]: WASAPI Loopback (Captures internal PC Audio / YouTube / Games)")
            for d in p.get_loopback_device_info_generator():
                print(f"    * {d['name']}")
            p.terminate()
        except Exception:
            pass

    if HAS_SD:
        devices = sd.query_devices()
        for idx, dev in enumerate(devices):
            dev = cast(dict, dev)
            channels_in = dev.get("max_input_channels", 0)
            name = dev.get("name", "Unknown")
            hostapi = dev.get("hostapi", 0)
            api_name = sd.query_hostapis(hostapi).get("name", "") if hostapi is not None else ""
            if channels_in > 0:
                openable, sr = is_device_openable(idx)
                status = f"[Ready - {sr}Hz]" if openable else "[Unavailable / Error]"
                hint = ""
                if "stereo mix" in name.lower():
                    hint = " (Stereo Mix)"
                elif "cable output" in name.lower() or "virtual" in name.lower():
                    hint = " (Virtual Cable)"
                print(f"  [{idx:2d}] IN:  {name} ({api_name}){hint} -> {status}")
    print("\nUse '--mode loopback' for internal audio (YouTube/Games), or '--mode mic' for Microphone.")
    print("Example: python live_translate_windows.py --mode loopback\n")


def auto_detect_input_device() -> Tuple[Optional[int], str, int]:
    """Auto-detect suitable, openable microphone input device."""
    if not HAS_SD:
        return None, "None", 16000
    devices = sd.query_devices()

    # 1. System default input
    try:
        default_in = sd.default.device[0]
        if default_in is not None and default_in >= 0:
            openable, sr = is_device_openable(default_in)
            if openable:
                dev_info = cast(dict, sd.query_devices(default_in))
                return default_in, dev_info.get("name", "Default Input"), sr
    except Exception:
        pass

    # 2. Any openable input
    for idx, dev in enumerate(devices):
        dev = cast(dict, dev)
        if dev.get("max_input_channels", 0) > 0:
            openable, sr = is_device_openable(idx)
            if openable:
                return idx, dev.get("name", f"Device {idx}"), sr

    return None, "None", 16000


class ConsoleOverlay:
    """Terminal output overlay (--no-window)."""
    def __init__(self, stop_event, show_partial=False):
        self.stop_event = stop_event
        self.show_partial = show_partial

    def post_pair(self, source, translated, **kwargs):
        if source:
            print("\n[Original]   ", source)
        if translated:
            print("[Translation]", translated, flush=True)

    def post_source(self, source, **kwargs):
        if source:
            print("\n[Speech]     ", source, flush=True)

    def post_status_text(self, text, **kwargs):
        if text:
            print(f"[*] {text}", flush=True)

    def post_partial(self, source):
        if self.show_partial and source:
            print(f"~ {source}", flush=True)

    def run(self):
        while not self.stop_event.is_set():
            time.sleep(0.2)

    def stop(self):
        self.stop_event.set()


class TkinterOverlay:
    """Floating, translucent, modern bilingual overlay window for Windows."""
    def __init__(self, stop_event, title="Live Translation (Windows)", width=780, height=380, opacity=0.92, show_partial=False, on_switch_source=None):
        self.stop_event = stop_event
        self.title = title
        self.width = width
        self.height = height
        self.opacity = opacity
        self.show_partial = show_partial
        self.on_switch_source = on_switch_source
        self.msg_queue = queue.Queue()
        
        # Tk root
        self.root = tk.Tk()
        self.root.title(title)
        self.root.geometry(f"{width}x{height}+80+80")
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", opacity)
        self.root.configure(bg="#0f1117")
        
        # Drag support
        self._drag_data = {"x": 0, "y": 0}
        
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        # Header / Titlebar
        header = tk.Frame(self.root, bg="#161922", height=36)
        header.pack(fill=tk.X, side=tk.TOP)
        
        title_label = tk.Label(header, text="  🌐 Live Translation", font=("Segoe UI", 10, "bold"), fg="#00FFCC", bg="#161922")
        title_label.pack(side=tk.LEFT, pady=6)
        
        self.status_label = tk.Label(header, text="● Ready", font=("Segoe UI", 9), fg="#94A3B8", bg="#161922")
        self.status_label.pack(side=tk.LEFT, padx=10, pady=6)

        btn_clear = tk.Button(header, text="Clear", font=("Segoe UI", 8), fg="#E2E8F0", bg="#232936", 
                              relief="flat", padx=8, command=self.clear_text)
        btn_clear.pack(side=tk.RIGHT, padx=8, pady=4)

        header.bind("<ButtonPress-1>", self._start_drag)
        header.bind("<B1-Motion>", self._on_drag)
        title_label.bind("<ButtonPress-1>", self._start_drag)
        title_label.bind("<B1-Motion>", self._on_drag)

        # Content split frame: Left = Transcript, Right = Translation
        content = tk.Frame(self.root, bg="#0f1117")
        content.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Left Column (Original)
        left_box = tk.Frame(content, bg="#141721", bd=1, relief="solid")
        left_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 4))
        
        lbl_left = tk.Label(left_box, text="ORIGINAL SPEECH", font=("Segoe UI", 9, "bold"), fg="#94A3B8", bg="#141721")
        lbl_left.pack(anchor="w", padx=10, pady=(6, 2))
        
        self.txt_orig = tk.Text(left_box, bg="#141721", fg="#F8FAFC", font=("Segoe UI", 11), 
                                wrap=tk.WORD, bd=0, padx=10, pady=4)
        self.txt_orig.pack(fill=tk.BOTH, expand=True)

        # Right Column (Translation)
        right_box = tk.Frame(content, bg="#141721", bd=1, relief="solid")
        right_box.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(4, 0))
        
        lbl_right = tk.Label(right_box, text="TRANSLATION (THAI)", font=("Segoe UI", 9, "bold"), fg="#00FFCC", bg="#141721")
        lbl_right.pack(anchor="w", padx=10, pady=(6, 2))
        
        self.txt_trans = tk.Text(right_box, bg="#141721", fg="#00FFCC", font=("Segoe UI", 11), 
                                 wrap=tk.WORD, bd=0, padx=10, pady=4)
        self.txt_trans.pack(fill=tk.BOTH, expand=True)

    def _start_drag(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag(self, event):
        deltax = event.x - self._drag_data["x"]
        deltay = event.y - self._drag_data["y"]
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def clear_text(self):
        self.txt_orig.delete("1.0", tk.END)
        self.txt_trans.delete("1.0", tk.END)

    def on_close(self):
        self.stop_event.set()
        self.root.destroy()

    def post_pair(self, source, translated, **kwargs):
        self.msg_queue.put(("pair", source, translated))

    def post_source(self, source, **kwargs):
        self.msg_queue.put(("source", source, None))

    def post_status_text(self, text, **kwargs):
        self.msg_queue.put(("status", text, None))

    def post_partial(self, source):
        if self.show_partial:
            self.msg_queue.put(("partial", source, None))

    def _process_queue(self):
        try:
            while not self.msg_queue.empty():
                msg_type, val1, val2 = self.msg_queue.get_nowait()
                if msg_type == "pair":
                    if val1:
                        self.txt_orig.insert(tk.END, f"{val1}\n\n")
                        self.txt_orig.see(tk.END)
                    if val2:
                        self.txt_trans.insert(tk.END, f"{val2}\n\n")
                        self.txt_trans.see(tk.END)
                elif msg_type == "source":
                    if val1:
                        self.txt_orig.insert(tk.END, f"{val1}\n\n")
                        self.txt_orig.see(tk.END)
                elif msg_type == "status":
                    self.status_label.config(text=f"● {val1}")
        except Exception:
            pass

        if not self.stop_event.is_set():
            self.root.after(100, self._process_queue)
        else:
            self.root.destroy()

    def run(self):
        self.root.after(100, self._process_queue)
        self.root.mainloop()

    def stop(self):
        self.stop_event.set()


def resample_to_16k(audio: np.ndarray, orig_sr: int) -> np.ndarray:
    """Resample 1D float32 audio to 16,000 Hz using linear interpolation."""
    if orig_sr == 16000 or len(audio) == 0:
        return audio.astype(np.float32)
    target_len = int(len(audio) * 16000 / orig_sr)
    if target_len <= 0:
        return np.empty(0, dtype=np.float32)
    return np.interp(
        np.linspace(0, len(audio), target_len, endpoint=False),
        np.arange(len(audio)),
        audio,
    ).astype(np.float32)


def loopback_audio_capture_thread(audio_q, stop_event, block_seconds=0.5):
    """Continuously captures internal PC sound (YouTube/Games) via WASAPI Loopback."""
    if not HAS_PYAUDIO:
        print("[Audio Error] pyaudiowpatch is not installed!", file=sys.stderr)
        stop_event.set()
        return

    p = pyaudio.PyAudio()
    stream = None
    try:
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        
        loopback_dev = None
        for dev in p.get_loopback_device_info_generator():
            if default_speakers["name"] in dev["name"]:
                loopback_dev = dev
                break
        if loopback_dev is None:
            for dev in p.get_loopback_device_info_generator():
                loopback_dev = dev
                break

        if loopback_dev is None:
            raise RuntimeError("No WASAPI Loopback device found on this system.")

        dev_index = int(loopback_dev["index"])
        samplerate = int(loopback_dev.get("defaultSampleRate", 48000))
        channels = int(loopback_dev.get("maxInputChannels", 2))
        frames_per_buffer = max(512, int(samplerate * block_seconds))

        stream = p.open(
            format=pyaudio.paInt16,
            channels=channels,
            rate=samplerate,
            input=True,
            input_device_index=dev_index,
            frames_per_buffer=frames_per_buffer,
        )

        while not stop_event.is_set():
            try:
                data = stream.read(frames_per_buffer, exception_on_overflow=False)
            except Exception:
                continue
            if not data or stop_event.is_set():
                break

            arr = np.frombuffer(data, dtype=np.int16)
            if channels == 2:
                arr = arr.reshape(-1, 2).mean(axis=1)
            float_mono = (arr.astype(np.float32)) / 32768.0

            if samplerate != 16000:
                float_mono = resample_to_16k(float_mono, samplerate)

            audio_q.put(float_mono.copy())

    except Exception as exc:
        print(f"[Loopback Error] {exc}", file=sys.stderr)
        stop_event.set()
    finally:
        if stream:
            with contextlib.suppress(Exception):
                stream.stop_stream()
                stream.close()
        p.terminate()


def mic_audio_capture_thread(audio_q, stop_event, device, samplerate, block_seconds=0.5):
    """Continuously captures audio blocks from the chosen microphone and resamples to 16 kHz."""
    if not HAS_SD:
        print("[Audio Error] sounddevice is not installed!", file=sys.stderr)
        stop_event.set()
        return

    blocksize = max(256, int(samplerate * block_seconds))
    
    def callback(indata, frames, time_info, status):
        if not stop_event.is_set():
            mono = indata[:, 0] if indata.ndim > 1 else indata.flatten()
            if samplerate != 16000:
                mono = resample_to_16k(mono, samplerate)
            audio_q.put(mono.copy())

    try:
        with sd.InputStream(device=device, samplerate=samplerate, channels=1,
                            blocksize=blocksize, dtype="float32", callback=callback):
            while not stop_event.is_set():
                time.sleep(0.1)
    except Exception as exc:
        print(f"[Microphone Error] {exc}", file=sys.stderr)
        stop_event.set()


def processing_worker(
    audio_q,
    overlay,
    stop_event,
    whisper_model,
    translator,
    samplerate=16000,
    chunk_seconds=2.5,
    silence_rms=0.003,
    task="transcribe",
    source_lang="auto",
    target_lang="th",
):
    """Aggregates audio blocks, checks voice activity, transcribes with faster-whisper and translates."""
    buffer = []
    buffer_duration = 0.0
    overlay.post_status_text("Listening...")

    # Conversation history for translation context
    translation_history = []

    while not stop_event.is_set():
        try:
            block = audio_q.get(timeout=0.2)
            buffer.append(block)
            buffer_duration += len(block) / samplerate
        except queue.Empty:
            continue

        if buffer_duration >= chunk_seconds:
            audio_clip = np.concatenate(buffer, axis=0)
            buffer.clear()
            buffer_duration = 0.0

            # Energy / RMS check for speech
            rms = float(np.sqrt(np.mean(audio_clip**2)))
            if rms < silence_rms:
                continue

            overlay.post_status_text("Transcribing...")
            try:
                segments, info = whisper_model.transcribe(
                    audio_clip,
                    language=None if source_lang == "auto" else source_lang,
                    task=task,
                    beam_size=1,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=300),
                )
                text = " ".join([seg.text.strip() for seg in segments]).strip()
                
                if not text:
                    overlay.post_status_text("Listening...")
                    continue

                text = strip_hallucinations(text)
                if not text:
                    continue

                detected_lang = info.language or "auto"
                
                # Translation step
                if translator is not None:
                    overlay.post_status_text("Translating...")
                    try:
                        translated = translator.translate(
                            text,
                            history=translation_history[-3:],
                        )
                        if translated:
                            translation_history.append((text, translated))
                            if len(translation_history) > 10:
                                translation_history.pop(0)
                    except Exception as exc:
                        translated = f"[Translate Error: {exc}]"
                    overlay.post_pair(text, translated)
                else:
                    # Direct transcript
                    overlay.post_source(text)

                overlay.post_status_text("Listening...")

            except Exception as exc:
                print(f"[Whisper Error] {exc}", file=sys.stderr)
                overlay.post_status_text(f"Error: {exc}")


def parse_args():
    p = argparse.ArgumentParser(description="Live Translation for Windows")
    p.add_argument("--list", action="store_true", help="List audio input devices and exit")
    p.add_argument("--mode", default="loopback", choices=["loopback", "mic"], 
                   help="Audio source: 'loopback' for YouTube/Games, 'mic' for Microphone (default: loopback)")
    p.add_argument("--device", type=int, default=None, help="Microphone audio device index (see --list)")
    p.add_argument("--whisper", default="base", choices=WHISPER_MODELS, help="Whisper model size (default: base)")
    p.add_argument("--device-type", default="cpu", choices=["cpu", "cuda"], help="Inference device for faster-whisper")
    p.add_argument("--compute-type", default="int8", choices=["int8", "float16", "float32"], help="Compute quantization type")
    p.add_argument("--source", default="auto", help="Source spoken language (default: auto)")
    p.add_argument("--target", default="th", help="Target translation language (default: th)")
    p.add_argument("--chunk-seconds", type=float, default=2.5, help="Audio buffer chunk size in seconds (default: 2.5)")
    p.add_argument("--silence-rms", type=float, default=0.003, help="RMS energy threshold for silence (default: 0.003)")
    p.add_argument("--ollama-model", default="", help="Ollama model name (e.g. gemma2:2b, qwen2.5:3b)")
    p.add_argument("--gemini-key", default="", help="Google Gemini API key (or read from config.json)")
    p.add_argument("--whisper-translate", action="store_true", help="Use Whisper built-in translation to English (task=translate)")
    p.add_argument("--no-window", action="store_true", help="Console output only (no Tkinter overlay)")
    p.add_argument("--opacity", type=float, default=0.92, help="Window opacity 0.1-1.0 (default: 0.92)")
    p.add_argument("--width", type=int, default=780, help="Overlay window width (default: 780)")
    p.add_argument("--height", type=int, default=380, help="Overlay window height (default: 380)")
    return p.parse_args()


def main():
    args = parse_args()

    if args.list:
        list_devices()
        return

    config = load_config()

    # Determine Translation Backend
    translator = None
    trans_name = "None"
    gemini_key = args.gemini_key or config.get("translation", {}).get("gemini_api_key", "")
    gemini_model = config.get("translation", {}).get("gemini_model", "gemini-3.6-flash")

    if args.whisper_translate:
        print("[*] Whisper built-in translation to English enabled (task='translate').")
        trans_name = "Whisper Translate (EN)"
    elif args.ollama_model:
        print(f"[*] Initializing Ollama translator with model '{args.ollama_model}'...")
        translator = OllamaTranslator(
            model=args.ollama_model,
            target=args.target,
            url="http://127.0.0.1:11434",
            max_tokens=256,
            temperature=0.0,
            reasoning=False,
            source=args.source,
        )
        trans_name = f"Ollama ({args.ollama_model})"
    elif gemini_key:
        print(f"[*] Initializing Gemini AI translator ({gemini_model})...")
        try:
            translator = GeminiTranslator(
                api_key=gemini_key,
                model=gemini_model,
                target=args.target,
                source=args.source,
            )
            trans_name = f"Gemini ({gemini_model})"
        except Exception as e:
            print(f"[Warning] Failed to init GeminiTranslator: {e}, falling back...")
            translator = FallbackTranslator(target=args.target, source=args.source)
            trans_name = "TranslatePy Fallback"
    else:
        print("[*] No Gemini key or Ollama model; using multi-provider fallback (TranslatePy)...")
        translator = FallbackTranslator(target=args.target, source=args.source)
        trans_name = "TranslatePy"

    # Initialize Whisper model
    print(f"[*] Loading faster-whisper model '{args.whisper}' on {args.device_type} ({args.compute_type})...")
    from faster_whisper import WhisperModel
    whisper_model = WhisperModel(
        args.whisper,
        device=args.device_type,
        compute_type=args.compute_type,
    )
    print("[*] Whisper model loaded.")

    stop_event = threading.Event()
    audio_q = queue.Queue(maxsize=100)

    # Audio source setup
    use_loopback = (args.mode == "loopback")
    device_name = "System Audio (Loopback)"
    device_idx = args.device
    device_sr = 16000

    if not use_loopback:
        if device_idx is None:
            device_idx, device_name, device_sr = auto_detect_input_device()
            if device_idx is None:
                print("[Warning] No microphone found, switching to System Audio Loopback.")
                use_loopback = True
        else:
            info = cast(dict, sd.query_devices(device_idx)) if HAS_SD else {}
            device_name = info.get("name", f"Mic Device {device_idx}")
            device_sr = int(info.get("default_samplerate", 16000)) if info else 16000

    print(f"[*] Audio source: {device_name}")

    # UI Overlay
    title_str = f"Live Translation — [{device_name}] ➔ [{trans_name}]"
    if args.no_window:
        overlay = ConsoleOverlay(stop_event)
    else:
        overlay = TkinterOverlay(
            stop_event,
            title=title_str,
            width=args.width,
            height=args.height,
            opacity=args.opacity,
        )

    # Worker thread
    task_mode = "translate" if (args.whisper_translate or (args.target == "en" and not translator)) else "transcribe"
    worker_th = threading.Thread(
        target=processing_worker,
        args=(audio_q, overlay, stop_event, whisper_model, translator),
        kwargs={
            "samplerate": 16000,
            "chunk_seconds": args.chunk_seconds,
            "silence_rms": args.silence_rms,
            "task": task_mode,
            "source_lang": args.source,
            "target_lang": args.target,
        },
        daemon=True,
    )
    worker_th.start()

    # Audio Capture Thread
    if use_loopback:
        audio_th = threading.Thread(
            target=loopback_audio_capture_thread,
            args=(audio_q, stop_event, 0.5),
            daemon=True,
        )
    else:
        audio_th = threading.Thread(
            target=mic_audio_capture_thread,
            args=(audio_q, stop_event, device_idx, device_sr, 0.5),
            daemon=True,
        )
    audio_th.start()

    print("[*] Live translation is running! Play YouTube / game audio or speak into mic...")
    try:
        overlay.run()
    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        print("\n[*] Stopped.")


if __name__ == "__main__":
    main()
