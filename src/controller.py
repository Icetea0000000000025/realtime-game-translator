"""
Controller and Background Worker for Real-Time Screen, Fullscreen & Media Translator.
"""
import time
from typing import Dict, Any, Optional
from PyQt6.QtCore import QThread, pyqtSignal, QObject

from src.capture import ScreenCapture
from src.ocr import OCREngine
from src.translator import TranslationEngine
from src.utils import ConfigManager, calculate_similarity, clean_ocr_text


class TranslationWorker(QThread):
    """
    Background worker that continuously captures screen ROI or Fullscreen,
    performs OCR, checks text similarity, and translates new text.
    """
    new_subtitles = pyqtSignal(str, str)  # (thai_text, english_text)
    status_updated = pyqtSignal(str, str)  # (message, color_hex)
    ocr_detected = pyqtSignal(str)         # (raw_text)

    def __init__(self, config_mgr: ConfigManager):
        super().__init__()
        self.config_mgr = config_mgr
        self.config = self.config_mgr.config
        
        self.capture = ScreenCapture()
        self.ocr = OCREngine(self.config.get("ocr", {}))
        self.translator = TranslationEngine(self.config.get("translation", {}))

        self._is_running = False
        self._is_paused = False
        self._is_fullscreen = bool(self.config.get("app", {}).get("is_fullscreen", False))
        self._last_ocr_text = ""
        self._last_translated_thai = ""

    def update_settings(self):
        """Reloads settings from config manager."""
        self.config = self.config_mgr.config
        self.ocr.update_config(self.config.get("ocr", {}))
        self.translator.update_config(self.config.get("translation", {}))
        self._is_fullscreen = bool(self.config.get("app", {}).get("is_fullscreen", False))

    def set_fullscreen_mode(self, enable: bool):
        """Toggles between fullscreen scanning and ROI box scanning."""
        self._is_fullscreen = enable
        self.config["app"]["is_fullscreen"] = enable
        self.config_mgr.save_config(self.config)
        self._last_ocr_text = ""
        mode_str = "🖥️ โหมดทั้งหน้าจอ (Fullscreen)" if enable else "🎯 โหมดเฉพาะพื้นที่ (ROI Box)"
        self.status_updated.emit(f"เปลี่ยนเป็น {mode_str}", "#00FFCC")

    def set_roi(self, roi: Dict[str, int]):
        """Updates region of interest and switches to ROI mode."""
        self.config["roi"] = roi
        self.config["app"]["is_fullscreen"] = False
        self._is_fullscreen = False
        self.config_mgr.save_config(self.config)
        self._last_ocr_text = ""
        self.trigger_snapshot_translate()

    def start_worker(self):
        """Starts worker loop."""
        self._is_running = True
        self._is_paused = False
        if not self.isRunning():
            self.start()

    def pause_worker(self):
        """Pauses translation loop."""
        self._is_paused = True
        self.status_updated.emit("⏸️ หยุดชั่วคราว (กด F8 เพื่อทำงานต่อ)", "#FFAA00")

    def resume_worker(self):
        """Resumes translation loop."""
        self._is_paused = False
        self.status_updated.emit("▶️ กำลังตรวจจับข้อความสด...", "#00FFCC")

    def toggle_pause(self) -> bool:
        """Toggles between paused and active."""
        if self._is_paused:
            self.resume_worker()
            return False
        else:
            self.pause_worker()
            return True

    def stop_worker(self):
        """Stops the worker thread."""
        self._is_running = False
        self.wait(1000)

    def trigger_snapshot_translate(self):
        """Immediately captures the screen/ROI and translates once (F7)."""
        try:
            if self._is_fullscreen:
                frame = self.capture.capture_fullscreen()
            else:
                roi = self.config.get("roi", {})
                frame = self.capture.capture_roi(roi)

            if frame is None or frame.size == 0:
                return

            raw_text = self.ocr.extract_text(frame)
            cleaned_text = clean_ocr_text(raw_text)
            if not cleaned_text or len(cleaned_text) < 2:
                return

            self.ocr_detected.emit(cleaned_text)
            self.status_updated.emit("⚡ กำลังแปลทันที (Snapshot)...", "#FFFF00")
            
            thai_text = self.translator.translate(cleaned_text)
            if thai_text:
                self._last_ocr_text = cleaned_text
                self._last_translated_thai = thai_text
                self.new_subtitles.emit(thai_text, cleaned_text)
                self.status_updated.emit("✅ แปลสำเร็จ", "#00FFCC")
        except Exception as e:
            print(f"[TranslationWorker] Snapshot translate error: {e}")

    def run(self):
        """Main background processing loop."""
        self.status_updated.emit("▶️ กำลังตรวจจับข้อความสด...", "#00FFCC")

        while self._is_running:
            if self._is_paused:
                self.msleep(200)
                continue

            interval_ms = int(self.config.get("app", {}).get("interval_ms", 500))
            similarity_threshold = float(self.config.get("app", {}).get("similarity_threshold", 0.85))

            try:
                # 1. Capture Fullscreen or ROI
                if self._is_fullscreen:
                    frame = self.capture.capture_fullscreen()
                else:
                    roi = self.config.get("roi", {})
                    frame = self.capture.capture_roi(roi)

                if frame is None or frame.size == 0:
                    self.msleep(interval_ms)
                    continue

                # 2. Extract Text via OCR
                raw_text = self.ocr.extract_text(frame)
                cleaned_text = clean_ocr_text(raw_text)

                if not cleaned_text or len(cleaned_text) < 2:
                    self.msleep(interval_ms)
                    continue

                # 3. Debounce / Similarity check
                similarity = calculate_similarity(cleaned_text, self._last_ocr_text)
                if similarity >= similarity_threshold:
                    self.msleep(interval_ms)
                    continue

                # New text detected!
                self._last_ocr_text = cleaned_text
                self.ocr_detected.emit(cleaned_text)

                # 4. Translate text
                self.status_updated.emit("⚡ กำลังแปลภาษา...", "#FFFF00")
                thai_text = self.translator.translate(cleaned_text)
                
                if thai_text:
                    self._last_translated_thai = thai_text
                    self.new_subtitles.emit(thai_text, cleaned_text)
                    self.status_updated.emit("✅ แปลสำเร็จ", "#00FFCC")

            except Exception as e:
                print(f"[TranslationWorker] Loop error: {e}")
                self.status_updated.emit(f"⚠️ Error: {e}", "#FF4444")

            self.msleep(interval_ms)

        self.capture.close()
