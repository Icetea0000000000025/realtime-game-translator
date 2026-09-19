"""
OCR Engine Module supporting Windows Native OCR (WinOCR) and Tesseract.
"""
from typing import Dict, Any, Optional
import numpy as np
import cv2
from src.utils import preprocess_image, clean_ocr_text

try:
    import winocr
    HAS_WINOCR = True
except ImportError:
    HAS_WINOCR = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False


class OCREngine:
    """Unified OCR Engine interface."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "engine": "winocr",
            "lang": "en",
            "upscale_factor": 1.5,
            "contrast_enhance": True,
            "binarize": False
        }
        self.engine_type = self.config.get("engine", "winocr").lower()
        self.lang = self.config.get("lang", "en")

    def update_config(self, config: Dict[str, Any]):
        """Updates OCR configuration."""
        self.config.update(config)
        self.engine_type = self.config.get("engine", "winocr").lower()
        self.lang = self.config.get("lang", "en")

    def extract_text(self, image: np.ndarray) -> str:
        """
        Runs OCR on given image array (BGR or Grayscale).
        Args:
            image: numpy ndarray of the screen region.
        Returns:
            Extracted text as a clean string.
        """
        if image is None or image.size == 0:
            return ""

        # Preprocessing image for improved readability
        processed = preprocess_image(
            image,
            upscale_factor=float(self.config.get("upscale_factor", 1.5)),
            contrast_enhance=bool(self.config.get("contrast_enhance", True)),
            binarize=bool(self.config.get("binarize", False))
        )

        extracted_text = ""

        if self.engine_type == "tesseract" and HAS_TESSERACT:
            extracted_text = self._run_tesseract(processed)
            if not extracted_text and HAS_WINOCR:
                extracted_text = self._run_winocr(processed)
        elif HAS_WINOCR:
            extracted_text = self._run_winocr(processed)
        elif HAS_TESSERACT:
            extracted_text = self._run_tesseract(processed)

        return clean_ocr_text(extracted_text)

    def _run_winocr(self, image: np.ndarray) -> str:
        """Runs Windows Media OCR."""
        try:
            # If image is grayscale, convert to BGR for winocr.recognize_cv2_sync
            if len(image.shape) == 2:
                bgr_img = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            else:
                bgr_img = image

            result = winocr.recognize_cv2_sync(bgr_img, self.lang)
            return result.get("text", "") if isinstance(result, dict) else str(result)
        except Exception as e:
            print(f"[OCREngine] WinOCR Error: {e}")
            return ""

    def _run_tesseract(self, image: np.ndarray) -> str:
        """Runs Tesseract OCR."""
        try:
            config_str = "--psm 6"  # Assume uniform block of text
            text = pytesseract.image_to_string(image, lang=self.lang, config=config_str)
            return text
        except Exception as e:
            print(f"[OCREngine] Tesseract Error: {e}")
            return ""
