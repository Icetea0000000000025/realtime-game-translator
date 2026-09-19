"""
Screen Capture Module using mss for high-performance ROI and Fullscreen capture.
"""
from typing import Dict, Optional, Tuple
import mss
import numpy as np


class ScreenCapture:
    """Handles high-speed screen capturing for specified ROI or Fullscreen."""

    def __init__(self):
        self._sct = mss.mss()

    def get_monitors(self):
        """Returns list of available monitors."""
        return self._sct.monitors

    def get_primary_monitor_size(self) -> Tuple[int, int]:
        """Returns (width, height) of the primary monitor."""
        if len(self._sct.monitors) > 1:
            mon = self._sct.monitors[1]
            return mon["width"], mon["height"]
        mon = self._sct.monitors[0]
        return mon["width"], mon["height"]

    def capture_fullscreen(self) -> Optional[np.ndarray]:
        """Captures entire primary monitor."""
        try:
            mon = self._sct.monitors[1] if len(self._sct.monitors) > 1 else self._sct.monitors[0]
            sct_img = self._sct.grab(mon)
            frame = np.array(sct_img)
            if frame.shape[2] == 4:
                frame = frame[:, :, :3]
            return frame
        except Exception as e:
            print(f"[ScreenCapture] Error capturing fullscreen: {e}")
            return None

    def capture_roi(self, roi: Dict[str, int]) -> Optional[np.ndarray]:
        """
        Captures a region of interest.
        Args:
            roi: Dictionary with keys 'left', 'top', 'width', 'height'.
        Returns:
            np.ndarray: Image in BGR format (3 channels) or None if invalid.
        """
        try:
            left = int(roi.get("left", 0))
            top = int(roi.get("top", 0))
            width = int(roi.get("width", 100))
            height = int(roi.get("height", 100))

            if width <= 0 or height <= 0:
                return None

            monitor_roi = {
                "left": left,
                "top": top,
                "width": width,
                "height": height
            }

            sct_img = self._sct.grab(monitor_roi)
            frame = np.array(sct_img)
            if frame.shape[2] == 4:
                frame = frame[:, :, :3]

            return frame
        except Exception as e:
            print(f"[ScreenCapture] Error capturing ROI {roi}: {e}")
            return None

    def close(self):
        """Closes mss instance."""
        if hasattr(self, "_sct") and self._sct:
            self._sct.close()
