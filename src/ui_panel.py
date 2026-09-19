"""
Modern Control Panel GUI for Real-Time Screen, Fullscreen & System Audio Translator (PyQt6).
"""
import os
from typing import Optional, Dict, Any
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QSpinBox, QSlider,
    QCheckBox, QGroupBox, QTextEdit, QTabWidget, QProgressBar,
    QMessageBox, QRadioButton, QButtonGroup, QScrollArea
)

from src.utils import ConfigManager


DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #111319;
    color: #E2E8F0;
    font-family: 'Segoe UI', 'Sarabun', sans-serif;
    font-size: 13px;
}

QTabWidget::pane {
    border: 1px solid #232936;
    background-color: #171B26;
    border-radius: 8px;
    padding: 12px;
}

QTabBar::tab {
    background: #131620;
    color: #94A3B8;
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
}

QTabBar::tab:selected {
    background: #1E2433;
    color: #00FFCC;
    border-bottom: 2px solid #00FFCC;
}

QGroupBox {
    border: 1px solid #232936;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: bold;
    color: #00FFCC;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
}

QPushButton {
    background-color: #242B3B;
    color: #FFFFFF;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 8px 14px;
    font-weight: bold;
    min-height: 24px;
}

QPushButton:hover {
    background-color: #2F394D;
    border-color: #00FFCC;
}

QPushButton:pressed {
    background-color: #1A202C;
}

QPushButton#btn_primary {
    background-color: #008766;
    border: 1px solid #00FFCC;
    color: #FFFFFF;
}

QPushButton#btn_primary:hover {
    background-color: #00B388;
}

QPushButton#btn_action {
    background-color: #1E3A8A;
    border: 1px solid #3B82F6;
}

QPushButton#btn_action:hover {
    background-color: #2563EB;
}

QPushButton#btn_snapshot {
    background-color: #B45309;
    border: 1px solid #F59E0B;
}

QPushButton#btn_snapshot:hover {
    background-color: #D97706;
}

QLineEdit, QSpinBox, QComboBox, QTextEdit {
    background-color: #0C0E14;
    border: 1px solid #232936;
    border-radius: 6px;
    padding: 6px;
    color: #FFFFFF;
}

QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #00FFCC;
}

QProgressBar {
    border: 1px solid #232936;
    border-radius: 4px;
    background: #0C0E14;
    text-align: center;
    color: #FFFFFF;
    height: 14px;
}

QProgressBar::chunk {
    background-color: #00FFCC;
    border-radius: 3px;
}
"""


class ControlPanel(QMainWindow):
    """Main Settings and Control Dashboard for Screen, Fullscreen & System Audio Translator."""
    
    # Signals
    request_select_roi = pyqtSignal()
    request_bottom_roi = pyqtSignal()
    request_toggle_pause = pyqtSignal()
    request_toggle_lock = pyqtSignal()
    request_snapshot = pyqtSignal()
    toggle_fullscreen_mode = pyqtSignal(bool)
    toggle_audio_mode = pyqtSignal(bool)
    change_audio_source = pyqtSignal(str)
    toggle_roi_border_visibility = pyqtSignal(bool)
    config_updated = pyqtSignal()
    set_capture_mode = pyqtSignal(str)  # "roi", "fullscreen", "audio_only"

    def __init__(self, config_mgr: ConfigManager):
        super().__init__()
        self.config_mgr = config_mgr
        self.config = self.config_mgr.config
        
        self.setWindowTitle("🌐 Real-Time Screen & Audio Translator (EN/Any ➔ TH)")
        self.resize(750, 710)
        self.setStyleSheet(DARK_STYLESHEET)
        
        self._init_ui()
        self.load_settings_to_ui()

    def _init_ui(self):
        """Creates the GUI layout."""
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(10)

        # 1. Header Banner
        header = QHBoxLayout()
        title_label = QLabel("🌐 Real-Time Screen & Audio Translator", self)
        title_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #00FFCC;")
        header.addWidget(title_label)

        header.addStretch()
        self.status_badge = QLabel("● พร้อมทำงาน", self)
        self.status_badge.setStyleSheet("color: #00FFCC; font-weight: bold; background: #142E28; padding: 4px 12px; border-radius: 12px; border: 1px solid #00FFCC;")
        header.addWidget(self.status_badge)
        main_layout.addLayout(header)

        # 2. Capture Mode Bar
        mode_bar = QHBoxLayout()
        mode_bar.addWidget(QLabel("🖥️ โหมดจับ:"))
        
        self.btn_group_mode = QButtonGroup(self)
        self.rb_roi_mode = QRadioButton("🎯 จับภาพ ROI", self)
        self.rb_full_mode = QRadioButton("🖥️ ทั้งหน้าจอ", self)
        self.rb_audio_only_mode = QRadioButton("🔊 ฟังเสียงอย่างเดียว", self)
        self.rb_audio_only_mode.setStyleSheet("color: #00FFCC; font-weight: bold;")
        self.btn_group_mode.addButton(self.rb_roi_mode)
        self.btn_group_mode.addButton(self.rb_full_mode)
        self.btn_group_mode.addButton(self.rb_audio_only_mode)
        self.rb_roi_mode.setChecked(True)
        
        self.rb_roi_mode.toggled.connect(lambda checked: checked and self._on_capture_mode_changed("roi"))
        self.rb_full_mode.toggled.connect(lambda checked: checked and self._on_capture_mode_changed("fullscreen"))
        self.rb_audio_only_mode.toggled.connect(lambda checked: checked and self._on_capture_mode_changed("audio_only"))
        mode_bar.addWidget(self.rb_roi_mode)
        mode_bar.addWidget(self.rb_full_mode)
        mode_bar.addWidget(self.rb_audio_only_mode)
        
        btn_bot_roi = QPushButton("🎬 ซับด้านล่าง", self)
        btn_bot_roi.clicked.connect(self.request_bottom_roi.emit)
        mode_bar.addWidget(btn_bot_roi)
        mode_bar.addStretch()

        main_layout.addLayout(mode_bar)

        # 3. Main Tab Widget
        self.tabs = QTabWidget(self)
        self.tab_dashboard = QWidget()
        self.tab_settings = QWidget()
        self.tab_overlay = QWidget()
        self.tab_hotkeys = QWidget()

        self.tabs.addTab(self.tab_dashboard, "📊 หน้าควบคุม")
        self.tabs.addTab(self.tab_settings, "⚙️ ระบบแปล & เสียง & OCR")
        self.tabs.addTab(self.tab_overlay, "🎨 ปรับขนาด & รูปแบบซับ")
        self.tabs.addTab(self.tab_hotkeys, "⌨️ คีย์ลัด")

        self._build_dashboard_tab()
        self._build_settings_tab()
        self._build_overlay_tab()
        self._build_hotkeys_tab()

        main_layout.addWidget(self.tabs)

        # 4. Footer Action Controls
        footer = QHBoxLayout()
        
        self.btn_snapshot = QPushButton("⚡ แปลทันที (F7)", self)
        self.btn_snapshot.setObjectName("btn_snapshot")
        self.btn_snapshot.clicked.connect(self.request_snapshot.emit)
        footer.addWidget(self.btn_snapshot)

        self.btn_select_roi = QPushButton("🎯 ลากเลือกพื้นที่ใหม่ (F9)", self)
        self.btn_select_roi.setObjectName("btn_action")
        self.btn_select_roi.clicked.connect(self.request_select_roi.emit)
        footer.addWidget(self.btn_select_roi)

        self.btn_toggle_pause = QPushButton("⏸️ หยุดชั่วคราว (F8)", self)
        self.btn_toggle_pause.setObjectName("btn_primary")
        self.btn_toggle_pause.clicked.connect(self.request_toggle_pause.emit)
        footer.addWidget(self.btn_toggle_pause)

        self.btn_toggle_lock = QPushButton("🔒 ล็อกซับ / คลิกทะลุ (F10)", self)
        self.btn_toggle_lock.clicked.connect(self.request_toggle_lock.emit)
        footer.addWidget(self.btn_toggle_lock)

        main_layout.addLayout(footer)

    def _build_dashboard_tab(self):
        """Builds Dashboard tab with live preview & Audio Meter."""
        layout = QVBoxLayout(self.tab_dashboard)

        # Target Area Information Group
        roi_group = QGroupBox("📍 ข้อมูลพื้นที่กล้อง (Capture Area)")
        roi_layout = QHBoxLayout(roi_group)
        self.lbl_roi_info = QLabel("X: 400 | Y: 750 | กว้าง: 1120px | สูง: 220px", self)
        self.lbl_roi_info.setStyleSheet("color: #FFFFFF; font-size: 13px;")
        roi_layout.addWidget(self.lbl_roi_info)
        roi_layout.addStretch()
        
        self.chk_roi_border = QCheckBox("👁️ แสดงกรอบนีออน ROI", self)
        self.chk_roi_border.setChecked(True)
        self.chk_roi_border.toggled.connect(self.toggle_roi_border_visibility.emit)
        roi_layout.addWidget(self.chk_roi_border)

        btn_reselect = QPushButton("🎯 ลากใหม่ (F9)", self)
        btn_reselect.clicked.connect(self.request_select_roi.emit)
        roi_layout.addWidget(btn_reselect)
        layout.addWidget(roi_group)

        # Audio Voice Level Meter
        audio_group = QGroupBox("🔊 ระดับเสียงในคอม/คลิป (Internal Audio Level)")
        audio_layout = QHBoxLayout(audio_group)
        self.audio_meter = QProgressBar(self)
        self.audio_meter.setRange(0, 100)
        self.audio_meter.setValue(0)
        audio_layout.addWidget(self.audio_meter)
        self.lbl_audio_status = QLabel("พร้อมรับฟังเสียงในคอม", self)
        self.lbl_audio_status.setStyleSheet("color: #00FFCC; font-size: 11px;")
        audio_layout.addWidget(self.lbl_audio_status)
        layout.addWidget(audio_group)

        # Live Text Previews
        text_group = QGroupBox("💬 ตัวอย่างข้อความสด (Live Translation)")
        text_layout = QVBoxLayout(text_group)

        text_layout.addWidget(QLabel("ข้อความที่ตรวจพบจากภาพหรือเสียงพูด (Extracted / Voice):"))
        self.txt_ocr_preview = QTextEdit(self)
        self.txt_ocr_preview.setReadOnly(True)
        self.txt_ocr_preview.setMaximumHeight(65)
        self.txt_ocr_preview.setPlaceholderText("รอตรวจพบข้อความจากหน้าจอ (เกม / วิดีโอ / เสียงพูด)...")
        text_layout.addWidget(self.txt_ocr_preview)

        text_layout.addWidget(QLabel("คำแปลภาษาไทย (Subtitles):"))
        self.txt_thai_preview = QTextEdit(self)
        self.txt_thai_preview.setReadOnly(True)
        self.txt_thai_preview.setMaximumHeight(80)
        self.txt_thai_preview.setStyleSheet("color: #00FFCC; font-weight: bold; font-size: 14px;")
        self.txt_thai_preview.setPlaceholderText("คำแปลจะแสดงที่นี่และบนหน้าต่าง Overlay...")
        text_layout.addWidget(self.txt_thai_preview)

        layout.addWidget(text_group)

    def _build_settings_tab(self):
        """Builds Translation, Audio & OCR configuration tab."""
        layout = QVBoxLayout(self.tab_settings)

        # Audio Settings Group
        audio_set_group = QGroupBox("🔊 ตั้งค่าแหล่งกำเนิดเสียง (Audio Source)")
        audio_set_layout = QHBoxLayout(audio_set_group)
        audio_set_layout.addWidget(QLabel("อุปกรณ์เสียงที่ดักฟัง:"))
        self.cmb_audio_src = QComboBox(self)
        self.cmb_audio_src.addItems([
            "🔊 เสียงภายในคอมพิวเตอร์ (YouTube / เกม / วิดีโอ - WASAPI Loopback)",
            "🎙️ ไมโครโฟน (Microphone)"
        ])
        self.cmb_audio_src.currentIndexChanged.connect(self._on_audio_src_changed)
        audio_set_layout.addWidget(self.cmb_audio_src)
        layout.addWidget(audio_set_group)

        # Translation Engine Group
        trans_group = QGroupBox("🌐 เครื่องยนต์แปลภาษา (Translation Engine)")
        trans_layout = QVBoxLayout(trans_group)

        engine_row = QHBoxLayout()
        engine_row.addWidget(QLabel("Engine:"))
        self.cmb_engine = QComboBox(self)
        self.cmb_engine.addItems([
            "Auto (Multi-provider เร็ว & เสถียร ไม่จำกัด)",
            "Google Gemini AI (สำนวนเกม/สตรีม ฉลาดสุด)",
            "Google Translate"
        ])
        self.cmb_engine.currentIndexChanged.connect(self._on_engine_changed)
        engine_row.addWidget(self.cmb_engine)
        trans_layout.addLayout(engine_row)

        lang_row = QHBoxLayout()
        lang_row.addWidget(QLabel("ภาษาต้นทาง (Source):"))
        self.cmb_source_lang = QComboBox(self)
        self.cmb_source_lang.addItems(["Auto (ตรวจจับอัตโนมัติ)", "English (en)", "Japanese (ja)", "Chinese (zh)", "Korean (ko)"])
        lang_row.addWidget(self.cmb_source_lang)

        lang_row.addWidget(QLabel("ภาษาเป้าหมาย (Target):"))
        self.cmb_target_lang = QComboBox(self)
        self.cmb_target_lang.addItems(["Thai (ภาษาไทย - th)", "English (en)"])
        lang_row.addWidget(self.cmb_target_lang)
        trans_layout.addLayout(lang_row)

        # Gemini API Key section
        self.gemini_widget = QWidget()
        gemini_layout = QVBoxLayout(self.gemini_widget)
        gemini_layout.setContentsMargins(0, 4, 0, 0)
        
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("Gemini API Key:"))
        self.txt_gemini_key = QLineEdit(self)
        self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_gemini_key.setPlaceholderText("ใส่ Google Gemini API Key (ถ้าต้องการใช้ AI LLM)...")
        key_row.addWidget(self.txt_gemini_key)
        
        self.btn_show_key = QPushButton("👁️", self)
        self.btn_show_key.setFixedWidth(40)
        self.btn_show_key.clicked.connect(self._toggle_show_key)
        key_row.addWidget(self.btn_show_key)
        gemini_layout.addLayout(key_row)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Gemini Model:"))
        self.cmb_gemini_model = QComboBox(self)
        self.cmb_gemini_model.addItems(["gemini-3.6-flash", "gemini-3.6-pro", "gemini-2.5-flash", "gemini-2.5-pro"])
        model_row.addWidget(self.cmb_gemini_model)
        gemini_layout.addLayout(model_row)

        trans_layout.addWidget(self.gemini_widget)
        layout.addWidget(trans_group)

        # OCR & Performance Group
        ocr_group = QGroupBox("🔍 ระบบตรวจจับตัวอักษร & ความเร็ว (OCR & Capture)")
        ocr_layout = QVBoxLayout(ocr_group)

        ocr_row = QHBoxLayout()
        ocr_row.addWidget(QLabel("OCR Engine:"))
        self.cmb_ocr = QComboBox(self)
        self.cmb_ocr.addItems(["Windows Native OCR (WinOCR - แนะนำ เร็วมาก)", "Tesseract OCR"])
        ocr_row.addWidget(self.cmb_ocr)
        ocr_layout.addLayout(ocr_row)

        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("ความถี่ในการจับภาพ (มิลลิวินาที):"))
        self.spn_interval = QSpinBox(self)
        self.spn_interval.setRange(150, 3000)
        self.spn_interval.setSingleStep(50)
        self.spn_interval.setValue(500)
        interval_row.addWidget(self.spn_interval)
        ocr_layout.addLayout(interval_row)

        layout.addWidget(ocr_group)

        btn_save_settings = QPushButton("💾 บันทึกการตั้งค่าระบบ", self)
        btn_save_settings.setObjectName("btn_primary")
        btn_save_settings.clicked.connect(self.save_settings)
        layout.addWidget(btn_save_settings)
        layout.addStretch()

    def _build_overlay_tab(self):
        """Builds Appearance and Subtitle UI tab with Size adjustments."""
        layout = QVBoxLayout(self.tab_overlay)

        style_group = QGroupBox("🎨 การแสดงผลและขนาดกล่องซับไตเติล (Subtitle Box Size & Style)")
        style_layout = QVBoxLayout(style_group)

        # Box Dimensions
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("ความกว้างกล่องซับ (Width):"))
        self.spn_overlay_w = QSpinBox(self)
        self.spn_overlay_w.setRange(300, 3840)
        self.spn_overlay_w.setSingleStep(50)
        self.spn_overlay_w.setValue(1000)
        size_row.addWidget(self.spn_overlay_w)

        size_row.addWidget(QLabel("ความสูง (Height):"))
        self.spn_overlay_h = QSpinBox(self)
        self.spn_overlay_h.setRange(100, 2160)
        self.spn_overlay_h.setSingleStep(20)
        self.spn_overlay_h.setValue(160)
        size_row.addWidget(self.spn_overlay_h)
        style_layout.addLayout(size_row)

        # Font Size
        font_row = QHBoxLayout()
        font_row.addWidget(QLabel("ขนาดตัวอักษรภาษาไทย:"))
        self.slider_font_size = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_font_size.setRange(14, 42)
        self.lbl_font_size_val = QLabel("22 px", self)
        self.slider_font_size.valueChanged.connect(lambda v: self.lbl_font_size_val.setText(f"{v} px"))
        font_row.addWidget(self.slider_font_size)
        font_row.addWidget(self.lbl_font_size_val)
        style_layout.addLayout(font_row)

        # Opacity
        opacity_row = QHBoxLayout()
        opacity_row.addWidget(QLabel("ความทึบของพื้นหลังกล่องซับ:"))
        self.slider_opacity = QSlider(Qt.Orientation.Horizontal, self)
        self.slider_opacity.setRange(20, 100)
        self.lbl_opacity_val = QLabel("75 %", self)
        self.slider_opacity.valueChanged.connect(lambda v: self.lbl_opacity_val.setText(f"{v} %"))
        opacity_row.addWidget(self.slider_opacity)
        opacity_row.addWidget(self.lbl_opacity_val)
        style_layout.addLayout(opacity_row)

        self.chk_show_orig = QCheckBox("แสดงข้อความภาษาต้นทางคู่กับภาษาไทย", self)
        style_layout.addWidget(self.chk_show_orig)

        layout.addWidget(style_group)

        info_box = QLabel(
            "💡 <b>วิธีปรับขนาดด้วยเมาส์โดยตรง:</b><br>"
            "1. กด <b>F10</b> เพื่อปลดล็อกกล่องซับไตเติลบนหน้าจอ<br>"
            "2. นำเมาส์ไปชี้ที่<b>ขอบหรือมุมของกล่องซับ</b> เมาส์จะเปลี่ยนเป็นรูปลูกศรสองหัว ⬌ ⬍<br>"
            "3. <b>คลิกลากเพื่อย่อ/ขยายขนาดกล่องซับ</b> หรือคลิกตรงมุมขวาล่างเพื่อดึงขยายได้อิสระ<br>"
            "4. ปรับขนาดเสร็จแล้วกด <b>F10</b> อีกครั้งเพื่อล็อกกล่องซับให้คลิกทะลุได้",
            self
        )
        info_box.setStyleSheet("color: #00FFCC; padding: 12px; background: #131E24; border-radius: 6px; border: 1px solid #00AA88; line-height: 140%;")
        layout.addWidget(info_box)

        btn_save_overlay = QPushButton("💾 บันทึกและอัปเดตหน้าตาซับไตเติล", self)
        btn_save_overlay.setObjectName("btn_primary")
        btn_save_overlay.clicked.connect(self.save_settings)
        layout.addWidget(btn_save_overlay)
        layout.addStretch()

    def _build_hotkeys_tab(self):
        """Builds Hotkeys Reference tab."""
        layout = QVBoxLayout(self.tab_hotkeys)
        
        hotkey_group = QGroupBox("⌨️ รายการคีย์ลัดสากล (Global Hotkeys)")
        hk_layout = QVBoxLayout(hotkey_group)
        
        hk_layout.addWidget(QLabel("• <b>F7</b>: ⚡ แปลทันที 1 ครั้ง (Snapshot Translate)"))
        hk_layout.addWidget(QLabel("• <b>F8</b>: ▶️ เริ่มแปล / ⏸️ หยุดแปลชั่วคราว (Start / Pause Real-time loop)"))
        hk_layout.addWidget(QLabel("• <b>F9</b>: 🎯 ลากเมาส์ครอบพื้นที่ซับไตเติล/วิดีโอ/เกมใหม่ (Select Screen ROI)"))
        hk_layout.addWidget(QLabel("• <b>F10</b>: 🔒 สลับโหมดล็อกกล่องซับ (Click-Through คลิกทะลุ) / ปลดล็อกเพื่อเลื่อน/ย่อขยายขนาด"))
        hk_layout.addWidget(QLabel("• <b>ESC</b>: ยกเลิกการเลือกพื้นที่"))
        
        layout.addWidget(hotkey_group)
        layout.addStretch()

    def _on_capture_mode_changed(self, mode: str):
        """Handles switching between ROI, Fullscreen, and Audio-Only modes."""
        self.set_capture_mode.emit(mode)

    def _on_audio_src_changed(self, index: int):
        mode = "loopback" if index == 0 else "mic"
        self.change_audio_source.emit(mode)

    def _on_engine_changed(self, index: int):
        self.gemini_widget.setVisible(index == 1)

    def _toggle_show_key(self):
        if self.txt_gemini_key.echoMode() == QLineEdit.EchoMode.Password:
            self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.Normal)
            self.btn_show_key.setText("🔒")
        else:
            self.txt_gemini_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.btn_show_key.setText("👁️")

    def load_settings_to_ui(self):
        """Loads saved values from config into UI fields."""
        cfg = self.config
        
        # Capture Mode
        capture_mode = cfg.get("app", {}).get("capture_mode", "roi")
        # Backward compat: check old is_fullscreen flag
        if capture_mode == "roi" and cfg.get("app", {}).get("is_fullscreen", False):
            capture_mode = "fullscreen"
        if capture_mode == "audio_only":
            self.rb_audio_only_mode.setChecked(True)
        elif capture_mode == "fullscreen":
            self.rb_full_mode.setChecked(True)
        else:
            self.rb_roi_mode.setChecked(True)

        # Audio source
        audio_cfg = cfg.get("audio", {})
        mode = audio_cfg.get("mode", "loopback")
        self.cmb_audio_src.setCurrentIndex(0 if mode == "loopback" else 1)

        # ROI
        roi = cfg.get("roi", {})
        self.lbl_roi_info.setText(
            f"X: {roi.get('left', 400)} | Y: {roi.get('top', 750)} | "
            f"กว้าง: {roi.get('width', 1120)}px | สูง: {roi.get('height', 220)}px"
        )

        # Translation
        trans_cfg = cfg.get("translation", {})
        engine = trans_cfg.get("engine", "auto")
        if engine == "gemini":
            self.cmb_engine.setCurrentIndex(1)
        elif engine == "google":
            self.cmb_engine.setCurrentIndex(2)
        else:
            self.cmb_engine.setCurrentIndex(0)

        self.gemini_widget.setVisible(engine == "gemini")
        self.txt_gemini_key.setText(trans_cfg.get("gemini_api_key", ""))
        
        model = trans_cfg.get("gemini_model", "gemini-2.5-flash")
        idx = self.cmb_gemini_model.findText(model)
        if idx >= 0:
            self.cmb_gemini_model.setCurrentIndex(idx)

        # Languages
        src_lang = trans_cfg.get("source_lang", "auto")
        src_map = {"auto": 0, "en": 1, "ja": 2, "zh": 3, "ko": 4}
        self.cmb_source_lang.setCurrentIndex(src_map.get(src_lang, 0))

        # OCR & Interval
        app_cfg = cfg.get("app", {})
        self.spn_interval.setValue(app_cfg.get("interval_ms", 500))
        
        ocr_cfg = cfg.get("ocr", {})
        ocr_eng = ocr_cfg.get("engine", "winocr")
        self.cmb_ocr.setCurrentIndex(0 if ocr_eng == "winocr" else 1)

        # Overlay
        overlay_cfg = cfg.get("overlay", {})
        self.spn_overlay_w.setValue(overlay_cfg.get("width", 1000))
        self.spn_overlay_h.setValue(overlay_cfg.get("height", 160))
        
        font_size = overlay_cfg.get("font_size", 22)
        self.slider_font_size.setValue(font_size)
        self.lbl_font_size_val.setText(f"{font_size} px")

        opacity = int(overlay_cfg.get("bg_opacity", 0.75) * 100)
        self.slider_opacity.setValue(opacity)
        self.lbl_opacity_val.setText(f"{opacity} %")

        self.chk_show_orig.setChecked(overlay_cfg.get("show_original", True))
        self.chk_roi_border.setChecked(overlay_cfg.get("show_roi_border", True))

    def save_settings(self):
        """Saves values from UI back to config manager and emits update."""
        cfg = self.config
        
        # Audio source
        cfg.setdefault("audio", {})["mode"] = "loopback" if self.cmb_audio_src.currentIndex() == 0 else "mic"

        # Capture mode
        if self.rb_audio_only_mode.isChecked():
            capture_mode = "audio_only"
        elif self.rb_full_mode.isChecked():
            capture_mode = "fullscreen"
        else:
            capture_mode = "roi"

        # Translation
        engine_idx = self.cmb_engine.currentIndex()
        if engine_idx == 1:
            cfg["translation"]["engine"] = "gemini"
        elif engine_idx == 2:
            cfg["translation"]["engine"] = "google"
        else:
            cfg["translation"]["engine"] = "auto"

        cfg["translation"]["gemini_api_key"] = self.txt_gemini_key.text().strip()
        cfg["translation"]["gemini_model"] = self.cmb_gemini_model.currentText()

        src_indices = ["auto", "en", "ja", "zh", "ko"]
        cfg["translation"]["source_lang"] = src_indices[self.cmb_source_lang.currentIndex()]
        cfg["translation"]["target_lang"] = "th" if self.cmb_target_lang.currentIndex() == 0 else "en"

        # OCR & App
        cfg["ocr"]["engine"] = "winocr" if self.cmb_ocr.currentIndex() == 0 else "tesseract"
        cfg["app"]["interval_ms"] = self.spn_interval.value()
        cfg["app"]["is_fullscreen"] = capture_mode == "fullscreen"
        cfg["app"]["capture_mode"] = capture_mode

        # Overlay
        cfg["overlay"]["width"] = self.spn_overlay_w.value()
        cfg["overlay"]["height"] = self.spn_overlay_h.value()
        cfg["overlay"]["font_size"] = self.slider_font_size.value()
        cfg["overlay"]["bg_opacity"] = self.slider_opacity.value() / 100.0
        cfg["overlay"]["show_original"] = self.chk_show_orig.isChecked()
        cfg["overlay"]["show_roi_border"] = self.chk_roi_border.isChecked()

        self.config_mgr.save_config(cfg)
        self.config_updated.emit()

    def update_audio_level(self, level: int):
        """Updates the microphone / audio meter bar."""
        self.audio_meter.setValue(level)

    def update_roi_display(self, roi: Dict[str, int]):
        """Updates ROI label text."""
        self.lbl_roi_info.setText(
            f"X: {roi.get('left', 0)} | Y: {roi.get('top', 0)} | "
            f"กว้าง: {roi.get('width', 0)}px | สูง: {roi.get('height', 0)}px"
        )
        self.rb_roi_mode.setChecked(True)

    def update_overlay_size_display(self, width: int, height: int):
        """Syncs spinboxes when user resizes overlay with mouse."""
        self.spn_overlay_w.setValue(width)
        self.spn_overlay_h.setValue(height)

    def update_live_text(self, thai: str, english: str):
        """Updates preview textboxes in dashboard."""
        self.txt_thai_preview.setText(thai)
        self.txt_ocr_preview.setText(english)

    def update_status(self, message: str, color_hex: str):
        """Updates status badge in header."""
        self.status_badge.setText(message)
        self.status_badge.setStyleSheet(
            f"color: {color_hex}; font-weight: bold; background: #142E28; padding: 4px 12px; border-radius: 12px; border: 1px solid {color_hex};"
        )

    def update_pause_button(self, is_paused: bool):
        """Updates Pause/Resume button text."""
        if is_paused:
            self.btn_toggle_pause.setText("▶️ เริ่มทำงานต่อ (F8)")
            self.btn_toggle_pause.setStyleSheet("background-color: #008766; border: 1px solid #00FFCC;")
        else:
            self.btn_toggle_pause.setText("⏸️ หยุดชั่วคราว (F8)")
            self.btn_toggle_pause.setStyleSheet("")

    def update_lock_button(self, is_locked: bool):
        """Updates Lock/Unlock button text."""
        if is_locked:
            self.btn_toggle_lock.setText("🔓 ปลดล็อกซับ (F10)")
        else:
            self.btn_toggle_lock.setText("🔒 ล็อกซับ / คลิกทะลุ (F10)")
