"""Local translation backends used by the live overlay."""

import contextlib
import json
import os
import re
import sys
import threading
import time
from typing import Dict, Tuple, Optional
import urllib.error
import urllib.request

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from live_translation.text_pipeline import (
    live_translation_messages,
    strip_llm_noise,
)


class GlossaryManager:
    """Manages custom gaming glossary / dictionary for proper nouns and gamer terms."""

    def __init__(self, glossary_path: Optional[str] = None):
        if glossary_path is None:
            candidates = [
                os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "glossary.json"),
                os.path.join(os.getcwd(), "glossary.json"),
                "glossary.json",
            ]
            for p in candidates:
                if os.path.exists(p):
                    glossary_path = p
                    break
            if glossary_path is None:
                glossary_path = candidates[0]

        self.glossary_path = glossary_path
        self.terms: Dict[str, str] = {}
        self.load_glossary()

    def load_glossary(self):
        """Loads terms from glossary.json."""
        if os.path.exists(self.glossary_path):
            try:
                with open(self.glossary_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.terms = data.get("terms", {})
            except Exception as e:
                print(f"[GlossaryManager] Error reading glossary.json: {e}", file=sys.stderr)
                self.terms = {}
        else:
            self.terms = {}

    def mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Replaces glossary terms with unique placeholders before translation."""
        if not self.terms or not text:
            return text, {}

        placeholders: Dict[str, str] = {}
        masked_text = text
        sorted_terms = sorted(self.terms.items(), key=lambda x: len(x[0]), reverse=True)

        for i, (src_term, tgt_term) in enumerate(sorted_terms):
            if not src_term.strip():
                continue
            pattern = re.compile(rf"\b{re.escape(src_term)}\b", re.IGNORECASE)
            if pattern.search(masked_text):
                token = f"_GLO{i}X_"
                placeholders[token] = tgt_term
                masked_text = pattern.sub(token, masked_text)

        return masked_text, placeholders

    def unmask(self, text: str, placeholders: Dict[str, str]) -> str:
        """Restores placeholders with their user-defined target translation."""
        if not placeholders or not text:
            return text

        result = text
        for token, tgt_term in placeholders.items():
            pattern = re.compile(rf"\s*{re.escape(token)}\s*", re.IGNORECASE)
            result = pattern.sub(f" {tgt_term} ", result)

        return " ".join(result.split())


class FastGoogleTranslator:
    """
    Direct, ultra-fast Google Web Translate API client using HTTP Keep-Alive.
    Latency: ~80-250ms (5x - 10x faster than web scrapers / multi-provider wrappers).
    """

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
        }
        self.base_url = "https://translate.googleapis.com/translate_a/single"
        if HAS_REQUESTS:
            self.session = requests.Session()
            self.session.headers.update(self.headers)
        else:
            self.session = None

    def translate(self, text: str, source: str = "auto", target: str = "th") -> Optional[str]:
        if not text or not text.strip():
            return ""

        clients = ["dict-chrome-ex", "gtx"]
        for client in clients:
            try:
                params = {
                    "client": client,
                    "sl": source,
                    "tl": target,
                    "dt": "t",
                    "q": text,
                }
                if self.session:
                    resp = self.session.get(self.base_url, params=params, timeout=3.5)
                    if resp.status_code == 200:
                        resp.encoding = "utf-8"
                        data = resp.json()
                        if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                            result = "".join([part[0] for part in data[0] if part and part[0]])
                            if result:
                                return result.strip()
                else:
                    import urllib.parse
                    query_str = urllib.parse.urlencode(params)
                    req = urllib.request.Request(f"{self.base_url}?{query_str}", headers=self.headers)
                    with urllib.request.urlopen(req, timeout=3.5) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                            result = "".join([part[0] for part in data[0] if part and part[0]])
                            if result:
                                return result.strip()
            except Exception:
                continue

        return None


class LanguageSettings:
    def __init__(self, source, target, whisper_size="turbo", ollama_model="gemma4:26b-mlx"):
        self._lock = threading.Lock()
        self._source = source
        self._target = target
        self._whisper_size = whisper_size
        self._ollama_model = ollama_model

    def get(self):
        with self._lock:
            return self._source, self._target

    def get_whisper_size(self) -> str:
        with self._lock:
            return self._whisper_size

    def get_ollama_model(self) -> str:
        with self._lock:
            return self._ollama_model

    def set_source(self, source):
        with self._lock:
            self._source = source

    def set_target(self, target):
        with self._lock:
            self._target = target

    def set_whisper_size(self, whisper_size):
        with self._lock:
            self._whisper_size = whisper_size

    def set_ollama_model(self, ollama_model):
        with self._lock:
            self._ollama_model = ollama_model


class OllamaTranslator:
    def __init__(
        self,
        model,
        target,
        url,
        max_tokens,
        temperature,
        reasoning,
        source="auto",
        num_ctx=4096,
    ):
        self.model = model
        self.target = target
        self.source = source
        self.chat_url = url.rstrip("/") + "/api/chat"
        self.generate_url = url.rstrip("/") + "/api/generate"
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.reasoning = reasoning
        self.num_ctx = num_ctx

    def set_model(self, model):
        if model and model != self.model:
            previous, self.model = self.model, model
            if previous and previous != model:
                self._unload(previous)

    def _unload(self, model):
        """Best-effort: ask Ollama to drop a model from memory (keep_alive=0)."""
        payload = {"model": model, "prompt": "", "stream": False, "keep_alive": 0}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.generate_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
            if raw:
                body = json.loads(raw.decode("utf-8"))
                done_reason = body.get("done_reason")
                if done_reason not in (None, "unload"):
                    print(
                        f"[translate] Ollama did not confirm unload of {model}: {done_reason}",
                        file=sys.stderr,
                    )
        except urllib.error.URLError as exc:
            print(f"[translate] failed to unload {model}: {exc}", file=sys.stderr)

    def unload_models_except(self, models, keep_model):
        for model in models:
            if model and model != keep_model:
                self._unload(model)

    def set_target(self, target):
        self.target = target

    def set_source(self, source):
        self.source = source

    def translate(self, text, max_tokens=None, on_delta=None, history=None):
        num_predict = int(max_tokens or self.max_tokens)
        options = {
            "temperature": self.temperature,
            "num_predict": num_predict,
            "top_p": 0.8,
            "top_k": 20,
        }
        if self.num_ctx:
            options["num_ctx"] = int(self.num_ctx)
        stream = on_delta is not None and not self.reasoning
        payload = {
            "model": self.model,
            "messages": live_translation_messages(self.source, self.target, text, history),
            "stream": stream,
            "think": bool(self.reasoning),
            "keep_alive": "30m",
            "options": options,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.chat_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            if stream:
                return self._translate_stream(req, on_delta)
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Ollama is not responding. Run `ollama serve` and pull the model: "
                f"`ollama pull {self.model}`."
            ) from exc
        response = body.get("message", {}).get("content", "")
        return strip_llm_noise(response)

    def _translate_stream(self, req, on_delta, throttle_seconds=0.1):
        parts = []
        last_emit = 0.0
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue
                    chunk = json.loads(line)
                    delta = chunk.get("message", {}).get("content", "")
                    if delta:
                        parts.append(delta)
                        now = time.monotonic()
                        if now - last_emit >= throttle_seconds:
                            last_emit = now
                            with contextlib.suppress(Exception):
                                on_delta(strip_llm_noise("".join(parts)))
                    if chunk.get("done"):
                        break
        except urllib.error.URLError as exc:
            raise RuntimeError(
                "Ollama is not responding. Run `ollama serve` and pull the model: "
                f"`ollama pull {self.model}`."
            ) from exc
        final = strip_llm_noise("".join(parts))
        with contextlib.suppress(Exception):
            on_delta(final)
        return final


class GeminiTranslator:
    """Google Gemini AI low-latency translator with conversation history support."""
    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite", target: str = "th", source: str = "auto"):
        self.api_key = api_key
        self.model = model
        self.target = target
        self.source = source
        self._fallback = None
        self._cooldown_until = 0.0
        self._last_warn_time = 0.0
        from google import genai
        from google.genai import types
        self._types = types
        self.client = genai.Client(api_key=api_key)

    def set_target(self, target):
        self.target = target
        if self._fallback:
            self._fallback.set_target(target)

    def set_source(self, source):
        self.source = source
        if self._fallback:
            self._fallback.set_source(source)

    def translate(self, text, max_tokens=None, on_delta=None, history=None):
        if not text or not text.strip():
            return ""

        # If in rate-limit cooldown, directly use fast fallback without failing
        now = time.monotonic()
        if now < self._cooldown_until:
            if not self._fallback:
                self._fallback = FallbackTranslator(target=self.target, source=self.source)
            return self._fallback.translate(text, on_delta=on_delta)

        from live_translation.text_pipeline import live_translation_messages, strip_llm_noise
        msgs = live_translation_messages(self.source, self.target, text, history)
        
        prompt_parts = []
        for m in msgs:
            role = m.get("role", "user").upper()
            prompt_parts.append(f"[{role}]\n{m.get('content', '')}")
        prompt = "\n\n".join(prompt_parts)

        try:
            resp = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=self._types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=int(max_tokens or 400),
                    automatic_function_calling=self._types.AutomaticFunctionCallingConfig(disable=True),
                )
            )
            raw = (resp.text or "").strip() if resp else ""
            res = strip_llm_noise(raw)
            if on_delta:
                with contextlib.suppress(Exception):
                    on_delta(res)
            return res
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                self._cooldown_until = time.monotonic() + 30.0  # Cooldown 30s
                if time.monotonic() - self._last_warn_time > 60.0:
                    self._last_warn_time = time.monotonic()
                    print("[*] Gemini Free Tier quota reached (15 RPM). Auto-switched to Fast Fallback translator (cooldown 30s)...", file=sys.stderr)
            else:
                if time.monotonic() - self._last_warn_time > 30.0:
                    self._last_warn_time = time.monotonic()
                    print(f"[GeminiTranslator Warning] {err_str[:120]}, using fallback translator...", file=sys.stderr)

            if not self._fallback:
                self._fallback = FallbackTranslator(target=self.target, source=self.source)
            return self._fallback.translate(text, on_delta=on_delta)


class FallbackTranslator:
    """Ultra-fast, self-contained fallback translator using FastGoogleTranslator, Glossary, and TranslatePy."""
    def __init__(self, target: str = "th", source: str = "auto"):
        self.target = target
        self.source = source
        self._fast_google = FastGoogleTranslator()
        self._glossary = GlossaryManager()

        # In-memory translation cache (LRU)
        self._cache = {}

        try:
            from translatepy import Translator
            self._tp = Translator()
        except ImportError:
            self._tp = None

    def set_target(self, target):
        self.target = target

    def set_source(self, source):
        self.source = source

    def translate(self, text, max_tokens=None, on_delta=None, history=None):
        if not text or not text.strip():
            return ""

        clean = text.strip()

        # Check Cache
        cache_key = f"{self.source}->{self.target}:{clean.lower()}"
        if cache_key in self._cache:
            res = self._cache[cache_key]
            if on_delta:
                with contextlib.suppress(Exception):
                    on_delta(res)
            return res

        masked, placeholders = self._glossary.mask(clean)

        result = ""

        # 1. Try FastGoogleTranslator (100-250ms)
        try:
            tgt = "th" if self.target in ["th", "thai"] else self.target
            src = "auto" if self.source == "auto" else self.source
            res = self._fast_google.translate(masked, source=src, target=tgt)
            if res:
                result = res
        except Exception:
            pass

        # 2. TranslatePy Fallback
        if not result and self._tp:
            try:
                dest = "Thai" if self.target in ["th", "thai"] else self.target
                res = self._tp.translate(masked, dest)
                if res and hasattr(res, "result") and res.result:
                    out = str(res.result).strip()
                    if "\ufffd" not in out:
                        result = out
            except Exception:
                pass

        # 3. Deep-Translator Google backup
        if not result:
            try:
                from deep_translator import GoogleTranslator
                res = GoogleTranslator(source=self.source, target=self.target).translate(masked)
                if res:
                    result = res
            except Exception as e:
                print(f"[FallbackTranslator Error] {e}", file=sys.stderr)

        if not result:
            result = clean

        # Unmask glossary
        if placeholders:
            result = self._glossary.unmask(result, placeholders)

        # Store in cache (limit 2000 items)
        if len(self._cache) > 2000:
            self._cache.clear()
        self._cache[cache_key] = result

        if on_delta:
            with contextlib.suppress(Exception):
                on_delta(result)

        return result
