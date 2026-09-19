"""Local translation backends used by the live overlay."""

import contextlib
import json
import sys
import threading
import time
import urllib.error
import urllib.request

from live_translation.text_pipeline import (
    live_translation_messages,
    strip_llm_noise,
)


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
            # Model switch: free the previous one from VRAM right away instead of letting
            # Ollama keep it resident for keep_alive minutes (which would hold both the old
            # and the new model in memory at once). The new model loads on the next translate.
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
        # Stream tokens as they're generated so the UI can show the translation arriving
        # instead of waiting for the whole block. Disabled when reasoning is on (thinking
        # tokens would interleave) or when the caller doesn't want partials.
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
        """Read Ollama's newline-delimited streaming response, forwarding the growing
        translation to on_delta (throttled), and return the final cleaned text."""
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
        # Throttling may have skipped the last tokens — push the complete text once so the
        # live draft is whole even if the commit that follows is briefly delayed.
        with contextlib.suppress(Exception):
            on_delta(final)
        return final


class GeminiTranslator:
    """Google Gemini AI low-latency translator with conversation history support."""
    def __init__(self, api_key: str, model: str = "gemini-3.6-flash", target: str = "th", source: str = "auto"):
        self.api_key = api_key
        self.model = model
        self.target = target
        self.source = source
        from google import genai
        from google.genai import types
        self._types = types
        self.client = genai.Client(api_key=api_key)

    def set_target(self, target):
        self.target = target

    def set_source(self, source):
        self.source = source

    def translate(self, text, max_tokens=None, on_delta=None, history=None):
        if not text or not text.strip():
            return ""
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
                )
            )
            raw = (resp.text or "").strip() if resp else ""
            res = strip_llm_noise(raw)
            if on_delta:
                with contextlib.suppress(Exception):
                    on_delta(res)
            return res
        except Exception as e:
            print(f"[GeminiTranslator Warning] {e}, using fallback translator...", file=sys.stderr)
            if not hasattr(self, "_fallback") or self._fallback is None:
                self._fallback = FallbackTranslator(target=self.target, source=self.source)
            return self._fallback.translate(text, on_delta=on_delta)


class FallbackTranslator:
    """Fast local/online fallback translator using TranslatePy / Deep-Translator."""
    def __init__(self, target: str = "th", source: str = "auto"):
        self.target = target
        self.source = source
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
        if self._tp:
            try:
                dest = "Thai" if self.target in ["th", "thai"] else self.target
                res = self._tp.translate(text, dest)
                if res and hasattr(res, "result") and res.result:
                    out = str(res.result).strip()
                    if on_delta:
                        with contextlib.suppress(Exception):
                            on_delta(out)
                    return out
            except Exception:
                pass
        try:
            from deep_translator import GoogleTranslator
            res = GoogleTranslator(source=self.source, target=self.target).translate(text)
            if on_delta:
                with contextlib.suppress(Exception):
                    on_delta(res)
            return res
        except Exception as e:
            print(f"[FallbackTranslator Error] {e}", file=sys.stderr)
            return text
