"""
Real-Time Screen, Fullscreen & System Audio Voice Translator (EN/Any -> TH)
Main Application Entry Point with PyQt6, WASAPI Loopback, Speech-to-Text & Global Hotkeys
"""
import sys
import os
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QApplication

from src.utils import ConfigManager
from src.overlay import SubtitleOverlay, ROISelectorOverlay, ROIBorderOverlay
from src.ui_panel import ControlPanel
from src.controller import TranslationWorker
from src.audio_listener import AudioTranslatorWorker

try:
    import keyboard
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False


class HotkeyBridge(QObject):
    """Bridge to forward keyboard hook callbacks to PyQt Main Thread safely."""
    hotkey_f7_pressed = pyqtSignal()
    hotkey_f8_pressed = pyqtSignal()
    hotkey_f9_pressed = pyqtSignal()
    hotkey_f10_pressed = pyqtSignal()


class GameTranslatorApp:
    """Main Application Coordinator."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")

        # 1. Config Manager
        self.config_mgr = ConfigManager()

        # 2. UI Components
        self.roi = self.config_mgr.config.get("roi", {})
        self.overlay = SubtitleOverlay(self.config_mgr.config)
        self.roi_border = ROIBorderOverlay(self.roi)
        self.roi_selector = ROISelectorOverlay()
        self.panel = ControlPanel(self.config_mgr)

        is_fullscreen = self.config_mgr.config.get("app", {}).get("is_fullscreen", False)
        show_border = self.config_mgr.config.get("overlay", {}).get("show_roi_border", True)
        if show_border and not is_fullscreen:
            self.roi_border.show()
        else:
            self.roi_border.hide()

        # 3. Background Workers (Screen OCR & System Audio STT)
        self.worker = TranslationWorker(self.config_mgr)
        self.audio_worker = AudioTranslatorWorker(self.config_mgr)

        # 4. Hotkey Bridge
        self.hotkey_bridge = HotkeyBridge()

        # 5. Connect Signal & Slots
        self._connect_signals()

        # 6. Register Global Hotkeys
        self._setup_global_hotkeys()

        # Auto-start based on saved capture mode
        initial_mode = self.config_mgr.config.get("app", {}).get("capture_mode", "roi")
        self._capture_mode = initial_mode
        if initial_mode == "audio_only":
            self.worker.pause_worker()
            self.audio_worker.start_worker()

    def _connect_signals(self):
        """Connects signals across all modules."""
        # Panel Actions -> Application
        self.panel.request_snapshot.connect(self.trigger_snapshot)
        self.panel.request_select_roi.connect(self.start_roi_selection)
        self.panel.request_bottom_roi.connect(self.set_bottom_roi_preset)
        self.panel.request_toggle_pause.connect(self.toggle_pause)
        self.panel.request_toggle_lock.connect(self.toggle_lock)
        self.panel.set_capture_mode.connect(self.set_capture_mode)
        self.panel.change_audio_source.connect(self.audio_worker.set_audio_mode)
        self.panel.toggle_roi_border_visibility.connect(self.toggle_roi_border)
        self.panel.config_updated.connect(self.on_config_updated)

        # ROI Selector -> App / Worker / Panel / Border
        self.roi_selector.roi_selected.connect(self.on_roi_selected)
        self.roi_selector.selection_cancelled.connect(self.on_selection_cancelled)

        # Overlay Geometry -> Config
        self.overlay.position_changed.connect(self.on_overlay_moved)

        # Screen Worker Signals -> Overlay & Panel
        self.worker.new_subtitles.connect(self.on_new_subtitles)
        self.worker.status_updated.connect(self.panel.update_status)

        # Audio Worker Signals -> Overlay & Panel
        self.audio_worker.new_subtitles.connect(self.on_new_subtitles)
        self.audio_worker.audio_status.connect(self.panel.update_status)
        self.audio_worker.audio_level.connect(self.panel.update_audio_level)

        # Hotkeys -> Slots
        self.hotkey_bridge.hotkey_f7_pressed.connect(self.trigger_snapshot)
        self.hotkey_bridge.hotkey_f8_pressed.connect(self.toggle_pause)
        self.hotkey_bridge.hotkey_f9_pressed.connect(self.start_roi_selection)
        self.hotkey_bridge.hotkey_f10_pressed.connect(self.toggle_lock)

    def _setup_global_hotkeys(self):
        """Sets up system-wide global hotkeys."""
        if not HAS_KEYBOARD:
            print("[Hotkeys] 'keyboard' package not found, hotkeys disabled.")
            return

        try:
            hotkeys = self.config_mgr.config.get("app", {}).get("hotkeys", {})
            hk_f7 = hotkeys.get("snapshot_translate", "f7")
            hk_f8 = hotkeys.get("toggle_translation", "f8")
            hk_f9 = hotkeys.get("select_roi", "f9")
            hk_f10 = hotkeys.get("toggle_lock", "f10")

            keyboard.add_hotkey(hk_f7, lambda: self.hotkey_bridge.hotkey_f7_pressed.emit())
            keyboard.add_hotkey(hk_f8, lambda: self.hotkey_bridge.hotkey_f8_pressed.emit())
            keyboard.add_hotkey(hk_f9, lambda: self.hotkey_bridge.hotkey_f9_pressed.emit())
            keyboard.add_hotkey(hk_f10, lambda: self.hotkey_bridge.hotkey_f10_pressed.emit())
            print(f"[Hotkeys] Registered global hotkeys: {hk_f7}=Snapshot, {hk_f8}=Start/Pause, {hk_f9}=Select ROI, {hk_f10}=Lock/Unlock")
        except Exception as e:
            print(f"[Hotkeys] Warning registering hotkeys: {e}")

    def trigger_snapshot(self):
        """Triggers single instant snapshot translation."""
        self.worker.trigger_snapshot_translate()

    def set_capture_mode(self, mode: str):
        """Switches between ROI, Fullscreen, and Audio-Only modes.
        
        - 'roi': Screen OCR on selected area + optional audio
        - 'fullscreen': Screen OCR on full screen + optional audio
        - 'audio_only': No screen capture, only audio STT translation
        """
        self._capture_mode = mode
        self.config_mgr.config.setdefault("app", {})["capture_mode"] = mode
        
        if mode == "audio_only":
            # Stop screen OCR, start audio
            self.worker.pause_worker()
            self.roi_border.hide()
            self.audio_worker.start_worker()
            print("[App] Mode: Audio Only — OCR disabled, listening to audio")
        elif mode == "fullscreen":
            # Start screen OCR fullscreen + stop audio-only
            self.worker.set_fullscreen_mode(True)
            self.worker.resume_worker()
            self.roi_border.hide()
            self.audio_worker.stop_worker()
            print("[App] Mode: Fullscreen OCR")
        else:  # roi
            # Start screen OCR on ROI + stop audio-only
            self.worker.set_fullscreen_mode(False)
            self.worker.resume_worker()
            show_border = self.config_mgr.config.get("overlay", {}).get("show_roi_border", True)
            if show_border:
                self.roi_border.show()
            self.audio_worker.stop_worker()
            print("[App] Mode: ROI OCR")

    def set_bottom_roi_preset(self):
        """Automatically calculates and sets ROI to the bottom 25% of the primary monitor."""
        screen = QApplication.primaryScreen().geometry()
        w = int(screen.width() * 0.8)
        h = int(screen.height() * 0.22)
        left = int((screen.width() - w) / 2)
        top = int(screen.height() * 0.72)
        
        roi = {"left": left, "top": top, "width": w, "height": h}
        self.on_roi_selected(roi)

    def start_roi_selection(self):
        """Hides ControlPanel temporarily and opens fullscreen ROI selection overlay."""
        self.roi_border.hide()
        self.panel.hide()
        QTimer.singleShot(100, self.roi_selector.start_selection)

    def on_roi_selected(self, roi: dict):
        """Called when user finishes dragging ROI."""
        print(f"[App] New ROI Selected: {roi}")
        self.roi = roi
        self.worker.set_roi(roi)
        self.panel.update_roi_display(roi)
        self.roi_border.update_roi(roi)
        
        self.panel.show()
        show_border = self.config_mgr.config.get("overlay", {}).get("show_roi_border", True)
        if show_border and not self.worker._is_fullscreen:
            self.roi_border.show()

    def on_selection_cancelled(self):
        """Restore windows if selection was cancelled."""
        self.panel.show()
        show_border = self.config_mgr.config.get("overlay", {}).get("show_roi_border", True)
        if show_border and not self.worker._is_fullscreen:
            self.roi_border.show()

    def toggle_roi_border(self, visible: bool):
        """Shows or hides the glowing ROI border."""
        if visible and not self.worker._is_fullscreen:
            self.roi_border.show()
        else:
            self.roi_border.hide()

    def toggle_pause(self):
        """Toggles translation worker paused state."""
        is_paused = self.worker.toggle_pause()
        self.panel.update_pause_button(is_paused)

    def toggle_lock(self):
        """Toggles overlay click-through / lock state."""
        is_locked = self.overlay.toggle_lock()
        self.panel.update_lock_button(is_locked)

    def on_overlay_moved(self, geo: dict):
        """Saves new position and dimensions of subtitle overlay."""
        self.config_mgr.config["overlay"].update(geo)
        self.config_mgr.save_config()
        self.panel.update_overlay_size_display(geo.get("width", 1000), geo.get("height", 160))

    def on_config_updated(self):
        """Refreshes workers, border, and overlay on settings save."""
        self.worker.update_settings()
        self.audio_worker.update_settings()
        self.overlay.apply_config(self.config_mgr.config)
        show_border = self.config_mgr.config.get("overlay", {}).get("show_roi_border", True)
        self.toggle_roi_border(show_border)

    def on_new_subtitles(self, thai: str, english: str):
        """Updates subtitles display in both overlay and panel."""
        self.overlay.update_subtitles(thai, english)
        self.panel.update_live_text(thai, english)

    def run(self):
        """Starts the application."""
        self.panel.show()
        self.overlay.show()
        self.worker.start_worker()

        exit_code = self.app.exec()

        # Clean up
        if HAS_KEYBOARD:
            try:
                keyboard.unhook_all()
            except Exception:
                pass
        self.worker.stop_worker()
        self.audio_worker.stop_worker()
        sys.exit(exit_code)


def main():
    app = GameTranslatorApp()
    app.run()


if __name__ == "__main__":
    main()
