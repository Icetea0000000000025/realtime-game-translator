"""
Translation Engine Module supporting TranslatePy (Multi-provider Auto-failover),
Deep-Translator, and Gemini AI.
"""
import os
import sys
from typing import Dict, Any, Optional
from collections import OrderedDict

try:
    from translatepy import Translator as TranslatePyTranslator
    HAS_TRANSLATEPY = True
except ImportError:
    HAS_TRANSLATEPY = False

try:
    from deep_translator import GoogleTranslator
    HAS_DEEP_TRANSLATOR = True
except ImportError:
    HAS_DEEP_TRANSLATOR = False

try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False


class TranslationEngine:
    """Handles text translation with multi-provider failover and in-memory caching."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {
            "engine": "auto",  # "auto", "google", "gemini"
            "source_lang": "auto",
            "target_lang": "th",
            "gemini_api_key": "",
            "gemini_model": "gemini-3.6-flash"
        }
        self.engine_type = self.config.get("engine", "auto").lower()
        self.source_lang = self.config.get("source_lang", "auto")
        self.target_lang = self.config.get("target_lang", "th")
        
        # Translation Cache (Max 500 items, LRU)
        self.cache: OrderedDict[str, str] = OrderedDict()
        self.max_cache_size = 500

        # Initialized clients
        self._translatepy_client = None
        self._google_translator = None
        self._gemini_client = None
        self._init_engines()

    def _init_engines(self):
        """Initializes translation backends."""
        if HAS_TRANSLATEPY:
            try:
                self._translatepy_client = TranslatePyTranslator()
            except Exception as e:
                print(f"[TranslationEngine] TranslatePy init warning: {e}")

        if HAS_DEEP_TRANSLATOR:
            try:
                src = "auto" if self.source_lang == "auto" else self.source_lang
                self._google_translator = GoogleTranslator(
                    source=src,
                    target=self.target_lang
                )
            except Exception as e:
                print(f"[TranslationEngine] GoogleTranslator init warning: {e}")

        gemini_key = self.config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
        if HAS_GENAI and gemini_key:
            try:
                self._gemini_client = genai.Client(api_key=gemini_key)
            except Exception as e:
                print(f"[TranslationEngine] Gemini client init warning: {e}")

    def update_config(self, config: Dict[str, Any]):
        """Updates translation configuration and reinitializes if necessary."""
        self.config.update(config)
        self.engine_type = self.config.get("engine", "auto").lower()
        self.source_lang = self.config.get("source_lang", "auto")
        self.target_lang = self.config.get("target_lang", "th")
        self._init_engines()

    def translate(self, text: str) -> str:
        """
        Translates text from source language to target language.
        Returns translated string in UTF-8.
        """
        if not text or not text.strip():
            return ""

        clean_text = text.strip()

        # Check Cache
        cache_key = f"{self.engine_type}:{self.source_lang}->{self.target_lang}:{clean_text}"
        if cache_key in self.cache:
            self.cache.move_to_end(cache_key)
            return self.cache[cache_key]

        translated_text = ""

        # 1. If user specifically requested Gemini AI
        if self.engine_type == "gemini":
            translated_text = self._translate_gemini(clean_text)

        # 2. TranslatePy (Multi-provider Auto Failover: Google/Bing/Yandex/Reverso)
        if not translated_text and HAS_TRANSLATEPY:
            translated_text = self._translate_translatepy(clean_text)

        # 3. Deep-Translator Google backup
        if not translated_text and HAS_DEEP_TRANSLATOR:
            translated_text = self._translate_deep_translator(clean_text)

        # 4. Fallback to clean raw text if all network engines failed
        if not translated_text:
            translated_text = clean_text

        # Store in Cache
        self.cache[cache_key] = translated_text
        if len(self.cache) > self.max_cache_size:
            self.cache.popitem(last=False)

        return translated_text

    def _translate_translatepy(self, text: str) -> str:
        """Translates text using TranslatePy (automatic failover across top services)."""
        try:
            if not self._translatepy_client:
                self._translatepy_client = TranslatePyTranslator()
            
            target = "Thai" if self.target_lang in ["th", "thai"] else self.target_lang
            res = self._translatepy_client.translate(text, target)
            if res and hasattr(res, "result") and res.result:
                return str(res.result).strip()
            return ""
        except Exception as e:
            print(f"[TranslationEngine] TranslatePy error: {e}")
            return ""

    def _translate_deep_translator(self, text: str) -> str:
        """Translates text using Google Translator (deep-translator)."""
        try:
            if not self._google_translator:
                src = "auto" if self.source_lang == "auto" else self.source_lang
                self._google_translator = GoogleTranslator(
                    source=src,
                    target=self.target_lang
                )
            result = self._google_translator.translate(text)
            return result or ""
        except Exception as e:
            print(f"[TranslationEngine] deep-translator error: {e}")
            return ""

    def _translate_gemini(self, text: str) -> str:
        """Translates text using Gemini AI for high context / natural dialogue."""
        if not HAS_GENAI:
            return ""

        gemini_key = self.config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
        if not gemini_key:
            return ""

        try:
            if not self._gemini_client:
                self._gemini_client = genai.Client(api_key=gemini_key)

            model_name = self.config.get("gemini_model", "gemini-3.6-flash")
            target_lang = self.config.get("target_lang", "th")
            source_lang = self.config.get("source_lang", "auto")
            
            lang_names = {"th": "Thai", "en": "English", "ja": "Japanese", "zh": "Chinese", "ko": "Korean"}
            target_name = lang_names.get(target_lang, "Thai")
            source_hint = ""
            if source_lang != "auto":
                source_name = lang_names.get(source_lang, source_lang)
                source_hint = f"The source language is {source_name}. "
            
            prompt = (
                f"You are a real-time subtitle translator for games, YouTube, anime, movies, and live streams.\n"
                f"{source_hint}"
                f"Translate the following text into natural, fluent {target_name}.\n"
                f"Rules:\n"
                f"- Output ONLY the translated text, no quotes, no explanations, no notes.\n"
                f"- Use natural spoken/conversational style, not formal/academic.\n"
                f"- Preserve names, proper nouns, and game terms as-is or transliterate them.\n"
                f"- If the text is already in {target_name}, output it as-is.\n"
                f"- If the text is garbled/unreadable, output an empty string.\n\n"
                f"Text: {text}"
            )
            response = self._gemini_client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=500
                )
            )
            if response and response.text:
                result = response.text.strip()
                # Remove wrapping quotes if Gemini adds them
                if len(result) >= 2 and result[0] == '"' and result[-1] == '"':
                    result = result[1:-1]
                return result
            return ""
        except Exception as e:
            print(f"[TranslationEngine] Gemini API error: {e}")
            return ""
