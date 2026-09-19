import json
import os
import re
from difflib import SequenceMatcher
from typing import Any, Dict, Optional, Tuple
import cv2
import numpy as np

DEFAULT_CONFIG: Dict[str, Any] = {
    "roi": {
        "left": 400,
        "top": 750,
        "width": 1120,
        "height": 220
    },
    "overlay": {
        "x": 400,
        "y": 700,
        "width": 1120,
        "height": 180,
        "font_size": 22,
        "font_color": "#FFFFFF",
        "bg_color": "#000000",
        "bg_opacity": 0.75,
        "show_original": True,
        "click_through": False,
        "show_roi_border": True
    },
    "translation": {
        "engine": "auto",  # "auto", "gemini", "google"
        "source_lang": "auto",
        "target_lang": "th",
        "gemini_api_key": "",
        "gemini_model": "gemini-2.5-flash"
    },
    "ocr": {
        "engine": "winocr",
        "lang": "en",
        "upscale_factor": 1.5,
        "contrast_enhance": True,
        "binarize": False
    },
    "app": {
        "preset": "game",
        "interval_ms": 500,
        "similarity_threshold": 0.85,
        "hotkeys": {
            "snapshot_translate": "f7",
            "toggle_translation": "f8",
            "select_roi": "f9",
            "toggle_lock": "f10"
        }
    }
}

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")


class ConfigManager:
    """Manages application settings with json persistence."""

    def __init__(self, config_path: str = CONFIG_FILE_PATH):
        self.config_path = config_path
        self.config = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Loads config from JSON file, merging with default values."""
        if not os.path.exists(self.config_path):
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                saved_config = json.load(f)
            merged_config = DEFAULT_CONFIG.copy()
            for key, val in saved_config.items():
                if isinstance(val, dict) and key in merged_config and isinstance(merged_config[key], dict):
                    merged_config[key].update(val)
                else:
                    merged_config[key] = val
            return merged_config
        except Exception as e:
            print(f"[ConfigManager] Error reading config: {e}. Using defaults.")
            return DEFAULT_CONFIG.copy()

    def save_config(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Saves current config dictionary to JSON file."""
        if config is not None:
            self.config = config
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.config[key] = value
        self.save_config()


def preprocess_image(
    image: np.ndarray,
    upscale_factor: float = 1.5,
    contrast_enhance: bool = True,
    binarize: bool = False
) -> np.ndarray:
    """Preprocesses captured screenshot for optimal OCR accuracy."""
    if image is None or image.size == 0:
        return image

    processed = image.copy()

    # 1. Upscale if needed
    if upscale_factor > 1.0:
        h, w = processed.shape[:2]
        new_w, new_h = int(w * upscale_factor), int(h * upscale_factor)
        processed = cv2.resize(processed, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

    # 2. Grayscale
    if len(processed.shape) == 3:
        gray = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
    else:
        gray = processed

    # 3. Contrast enhancement
    if contrast_enhance:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray = clahe.apply(gray)

    # 4. Binarization
    if binarize:
        _, gray = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return gray


def clean_ocr_text(text: str) -> str:
    """
    Cleans raw OCR output and suppresses garbage sequences
    (like code line numbers 1 2 3 4 ... or pure punctuation noise).
    """
    if not text:
        return ""

    cleaned = text.strip()
    cleaned = re.sub(r"[\r\n]+", " ", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = cleaned.strip(" ~`|_^—=-#*")

    # If the text is purely numbers or sequence of line numbers (e.g. "36 37 38 39 40...")
    words = cleaned.split()
    if not words:
        return ""

    digits_count = sum(1 for w in words if w.isdigit())
    if len(words) > 3 and (digits_count / len(words)) > 0.6:
        # Strip out leading/trailing standalone digit runs
        cleaned_words = [w for w in words if not w.isdigit()]
        if not cleaned_words:
            return ""
        cleaned = " ".join(cleaned_words)

    return cleaned.strip()


def calculate_similarity(text1: str, text2: str) -> float:
    """Calculates similarity ratio between two strings (0.0 to 1.0)."""
    t1 = clean_ocr_text(text1).lower()
    t2 = clean_ocr_text(text2).lower()
    if not t1 and not t2:
        return 1.0
    if not t1 or not t2:
        return 0.0
    return SequenceMatcher(None, t1, t2).ratio()
