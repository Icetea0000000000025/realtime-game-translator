"""
PyQt6 Transparent Subtitle Overlay, ROI Border Indicator, and Screen Region Selector.
Supports Mouse Dragging to Move AND Dragging Edges/Corners to Resize freely.
"""
import sys
import ctypes
from typing import Optional, Dict, Any
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QCursor
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QSizeGrip,
    QGraphicsDropShadowEffect, QApplication
)

# Windows API constants for Click-Through
GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000


def set_click_through(hwnd: int, enable: bool = True):
    """Enables or disables click-through (pass mouse events to window underneath) on Windows."""
    try:
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        if enable:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED)
        else:
            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT)
    except Exception as e:
        print(f"[Overlay] Click-through setup warning: {e}")


class ROIBorderOverlay(QWidget):
    """
    Transparent frame that draws a visible glowing box around the currently captured ROI.
    """
    def __init__(self, roi: Optional[Dict[str, int]] = None):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.update_roi(roi or {"left": 400, "top": 750, "width": 1120, "height": 220})
        
        hwnd = int(self.winId())
        set_click_through(hwnd, enable=True)

    def update_roi(self, roi: Dict[str, int]):
        """Updates geometry to match ROI."""
        x = roi.get("left", 400)
        y = roi.get("top", 750)
        w = roi.get("width", 1120)
        h = roi.get("height", 220)
        self.setGeometry(x - 2, y - 2, w + 4, h + 4)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        pen = QPen(QColor(0, 255, 204, 180), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 4, 4)

        painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        painter.setPen(QColor(0, 255, 204, 220))
        painter.drawText(8, 14, "📸 Capture Area (ROI)")


class SubtitleOverlay(QWidget):
    """
    Transparent, Always-On-Top Subtitle Overlay Window.
    Supports movable/resizable mode (drag edges/corners to resize, drag center to move)
    and locked click-through mode.
    """
    position_changed = pyqtSignal(dict)

    # Edge margin for mouse resizing
    BORDER_MARGIN = 10

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.config = config or {}
        
        # State
        self.is_locked = False
        self._dragging = False
        self._resizing = False
        self._resize_edge = None
        self._drag_start_pos = QPoint()
        self._drag_start_geo = QRect()
        
        self.setMouseTracking(True)
        self._setup_window_flags()
        self._init_ui()
        self.apply_config(self.config)

    def _setup_window_flags(self):
        """Sets up window flags for transparent overlay."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

    def _init_ui(self):
        """Initializes UI elements and layout."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(18, 12, 18, 12)
        self.layout.setSpacing(6)

        # Status / Header bar (visible when unlocked)
        self.header_layout = QHBoxLayout()
        self.status_label = QLabel("🎮 [ปลดล็อก] - ลากขอบเพื่อปรับขนาด | ลากตรงกลางเพื่อย้าย | F10: ล็อกคลิกทะลุ", self)
        self.status_label.setStyleSheet("color: #00FFCC; font-size: 11px; font-weight: bold;")
        self.header_layout.addWidget(self.status_label)
        self.header_layout.addStretch()
        self.layout.addLayout(self.header_layout)

        # Thai Subtitle Label (Primary)
        self.thai_label = QLabel("รอข้อความจากหน้าจอ / เสียงในเกม...", self)
        self.thai_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thai_label.setWordWrap(True)
        self.thai_label.setStyleSheet(
            "color: #FFFFFF; font-size: 22px; font-weight: bold; font-family: 'Segoe UI', 'Sarabun', 'Tahoma', sans-serif;"
        )
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(8)
        shadow.setColor(QColor(0, 0, 0, 240))
        shadow.setOffset(2, 2)
        self.thai_label.setGraphicsEffect(shadow)
        self.layout.addWidget(self.thai_label)

        # English Subtitle Label (Secondary / Original)
        self.eng_label = QLabel("", self)
        self.eng_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.eng_label.setWordWrap(True)
        self.eng_label.setStyleSheet(
            "color: #CCCCCC; font-size: 15px; font-style: italic; font-family: 'Segoe UI', 'Sarabun', 'Tahoma', sans-serif;"
        )
        self.layout.addWidget(self.eng_label)

        # Bottom row with SizeGrip icon
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.sizegrip = QSizeGrip(self)
        self.sizegrip.setStyleSheet("width: 14px; height: 14px; background: transparent;")
        bottom_layout.addWidget(self.sizegrip)
        self.layout.addLayout(bottom_layout)

        self.setMinimumSize(300, 100)
        self.resize(1000, 160)

    def apply_config(self, config: Dict[str, Any]):
        """Applies styling and geometry from config."""
        overlay_cfg = config.get("overlay", {})
        x = overlay_cfg.get("x", 400)
        y = overlay_cfg.get("y", 700)
        w = overlay_cfg.get("width", 1000)
        h = overlay_cfg.get("height", 160)
        font_size = overlay_cfg.get("font_size", 22)
        font_color = overlay_cfg.get("font_color", "#FFFFFF")
        show_original = overlay_cfg.get("show_original", True)
        
        self.setGeometry(x, y, w, h)
        self.thai_label.setStyleSheet(
            f"color: {font_color}; font-size: {font_size}px; font-weight: bold; font-family: 'Segoe UI', 'Sarabun', 'Tahoma', sans-serif;"
        )
        self.eng_label.setVisible(show_original)
        self.update()

    def update_subtitles(self, thai_text: str, english_text: str = ""):
        """Updates displayed subtitles."""
        if thai_text:
            self.thai_label.setText(thai_text)
        else:
            self.thai_label.setText("")

        if self.eng_label.isVisible():
            self.eng_label.setText(english_text)

    def toggle_lock(self) -> bool:
        """Toggles between Moveable/Resizable Mode and Click-Through Mode."""
        self.set_lock(not self.is_locked)
        return self.is_locked

    def set_lock(self, lock: bool):
        """Sets lock / click-through state."""
        self.is_locked = lock
        hwnd = int(self.winId())
        set_click_through(hwnd, enable=self.is_locked)
        
        if self.is_locked:
            self.status_label.setVisible(False)
            self.sizegrip.setVisible(False)
            self.setCursor(Qt.CursorShape.ArrowCursor)
        else:
            self.status_label.setVisible(True)
            self.sizegrip.setVisible(True)
            self.status_label.setText("🔓 [ปลดล็อก] - ลากขอบ/มุมเพื่อปรับขนาด | ลากตรงกลางเพื่อย้าย | F10: ล็อก")
        
        self.update()

    def paintEvent(self, event):
        """Draws rounded background box."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg_opacity = 0.7 if not self.is_locked else 0.6
        bg_color = QColor(15, 15, 20, int(255 * bg_opacity))
        
        if not self.is_locked:
            border_pen = QPen(QColor(0, 255, 200, 200), 2, Qt.PenStyle.DashLine)
            painter.setPen(border_pen)
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        painter.setBrush(QBrush(bg_color))
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(rect, 12, 12)

    def _get_resize_edge(self, pos: QPoint) -> Optional[str]:
        """Detects if cursor is over a border edge/corner for resizing."""
        if self.is_locked:
            return None
            
        m = self.BORDER_MARGIN
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()

        left = x < m
        right = x > w - m
        top = y < m
        bottom = y > h - m

        if top and left:
            return "top_left"
        elif top and right:
            return "top_right"
        elif bottom and left:
            return "bottom_left"
        elif bottom and right:
            return "bottom_right"
        elif left:
            return "left"
        elif right:
            return "right"
        elif top:
            return "top"
        elif bottom:
            return "bottom"
        return None

    def mouseMoveEvent(self, event):
        if self.is_locked:
            return

        pos = event.pos()

        # If currently resizing
        if self._resizing and self._resize_edge:
            delta = event.globalPosition().toPoint() - self._drag_start_pos
            geo = QRect(self._drag_start_geo)
            
            if "right" in self._resize_edge:
                geo.setWidth(max(300, self._drag_start_geo.width() + delta.x()))
            if "bottom" in self._resize_edge:
                geo.setHeight(max(100, self._drag_start_geo.height() + delta.y()))
            if "left" in self._resize_edge:
                new_w = max(300, self._drag_start_geo.width() - delta.x())
                if new_w > 300:
                    geo.setLeft(self._drag_start_geo.left() + delta.x())
            if "top" in self._resize_edge:
                new_h = max(100, self._drag_start_geo.height() - delta.y())
                if new_h > 100:
                    geo.setTop(self._drag_start_geo.top() + delta.y())
            
            self.setGeometry(geo)
            event.accept()
            return

        # If currently moving
        if self._dragging:
            new_pos = event.globalPosition().toPoint() - self._drag_start_pos
            self.move(new_pos)
            event.accept()
            return

        # Update cursor based on hover edge
        edge = self._get_resize_edge(pos)
        if edge in ("top_left", "bottom_right"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif edge in ("top_right", "bottom_left"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif edge in ("left", "right"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif edge in ("top", "bottom"):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        else:
            self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mousePressEvent(self, event):
        if not self.is_locked and event.button() == Qt.MouseButton.LeftButton:
            edge = self._get_resize_edge(event.pos())
            if edge:
                self._resizing = True
                self._resize_edge = edge
                self._drag_start_pos = event.globalPosition().toPoint()
                self._drag_start_geo = self.geometry()
            else:
                self._dragging = True
                self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseReleaseEvent(self, event):
        if not self.is_locked and event.button() == Qt.MouseButton.LeftButton:
            if self._dragging or self._resizing:
                self._dragging = False
                self._resizing = False
                self._resize_edge = None
                self.position_changed.emit({
                    "x": self.x(),
                    "y": self.y(),
                    "width": self.width(),
                    "height": self.height()
                })
            event.accept()


class ROISelectorOverlay(QWidget):
    """
    Fullscreen semi-transparent overlay to drag and select screen Region of Interest (ROI).
    """
    roi_selected = pyqtSignal(dict)
    selection_cancelled = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._start_pos: Optional[QPoint] = None
        self._current_pos: Optional[QPoint] = None
        self._is_selecting = False

    def start_selection(self):
        """Displays fullscreen selector overlay across all screens."""
        screen_geo = QApplication.primaryScreen().virtualGeometry()
        self.setGeometry(screen_geo)
        self._start_pos = None
        self._current_pos = None
        self._is_selecting = False
        self.show()
        self.activateWindow()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.fillRect(self.rect(), QColor(0, 0, 0, 140))

        painter.setPen(QColor(255, 255, 255, 240))
        painter.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        instruction = "🎯 ลากเมาส์ครอบพื้นที่ซับไตเติล/วิดีโอ/เกมที่ต้องการแปล (กด ESC เพื่อยกเลิก)"
        painter.drawText(self.rect().adjusted(0, 40, 0, 0), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, instruction)

        if self._start_pos and self._current_pos:
            rect = QRect(self._start_pos, self._current_pos).normalized()
            
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            pen = QPen(QColor(0, 255, 204), 2, Qt.PenStyle.SolidLine)
            painter.setPen(pen)
            painter.drawRect(rect)

            badge_text = f"ROI: {rect.width()}x{rect.height()} (X:{rect.x()}, Y:{rect.y()})"
            painter.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            painter.setPen(QColor(0, 255, 204))
            painter.drawText(rect.x() + 8, max(rect.y() - 8, 25), badge_text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_pos = event.pos()
            self._current_pos = event.pos()
            self._is_selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self._is_selecting:
            self._current_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_selecting:
            self._is_selecting = False
            if self._start_pos and self._current_pos:
                rect = QRect(self._start_pos, self._current_pos).normalized()
                if rect.width() > 20 and rect.height() > 10:
                    roi = {
                        "left": rect.x(),
                        "top": rect.y(),
                        "width": rect.width(),
                        "height": rect.height()
                    }
                    self.roi_selected.emit(roi)
            self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.selection_cancelled.emit()
            self.close()
