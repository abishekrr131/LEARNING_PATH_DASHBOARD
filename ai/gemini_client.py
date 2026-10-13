"""Gemini Client and Prompt Engine.

Versioned templates with declared context keys, every call logged to ai_interactions,
and strict error propagation on API failure (no silent fake mocks).
"""
from __future__ import annotations

import logging
import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("palp.gemini")

PROMPT_DIR = Path(__file__).parent / "prompts"
_KEY = re.compile(r"\{\{(\w+)\}\}")


class GeminiUnavailableError(Exception):
    """Raised when Gemini API is unconfigured, unavailable, or fails."""
    pass


class GeminiRateLimitError(GeminiUnavailableError):
    """Raised when Gemini API responds with 429 Too Many Requests / ResourceExhausted."""
    pass


_VERIFIED_MODELS_CACHE: tuple[float, list[str]] = (0.0, [])


def get_verified_gemini_models(api_key: str | None = None, force_refresh: bool = False) -> list[str]:
    """Calls Google's ListModels API with the configured key and returns models supporting generateContent."""
    global _VERIFIED_MODELS_CACHE
    import json
    import time
    import urllib.request

    now = time.time()
    cache_time, cached = _VERIFIED_MODELS_CACHE
    if not force_refresh and cached and (now - cache_time < 300):
        return cached

    if not api_key:
        try:
            from backend.app.core.config import settings
            api_key = settings.GEMINI_API_KEY
        except Exception:
            api_key = os.getenv("GEMINI_API_KEY", "")

    if not api_key or api_key in ("your_gemini_api_key_here", ""):
        return []

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PALP-Adaptive/1.0"})
        with urllib.request.urlopen(req, timeout=12.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = []
            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    models.append(name)
            _VERIFIED_MODELS_CACHE = (now, models)
            logger.info("Fetched %d verified models from Google ListModels API", len(models))
            return models
    except Exception as e:
        logger.warning("Failed to fetch verified models via ListModels API: %s", e)
        return cached or []


def build_failover_order(
    primary_model: str,
    fallback_models_str: str | list[str] = "",
    verified_models: list[str] | None = None,
) -> list[str]:
    """Constructs failover model order strictly from verified models that support generateContent."""
    if isinstance(fallback_models_str, str):
        fallback_candidates = [m.strip() for m in fallback_models_str.split(",") if m.strip()]
    else:
        fallback_candidates = list(fallback_models_str)

    raw_candidates = [primary_model] + [m for m in fallback_candidates if m != primary_model]

    if not verified_models:
        deduped = []
        for m in raw_candidates:
            if m and m not in deduped:
                deduped.append(m)
        return deduped

    verified_set = set(verified_models)
    ordered = []
    # 1. Add configured primary and fallback models that are verified
    for m in raw_candidates:
        if m in verified_set and m not in ordered:
            ordered.append(m)

    # 2. If empty, pick any verified models containing flash
    if not ordered:
        for m in verified_models:
            if "flash" in m and "preview-tts" not in m and m not in ordered:
                ordered.append(m)

    return ordered


@dataclass(frozen=True)
class Template:
    name: str
    version: str
    model: str
    system: str
    body: str

    @property
    def required_keys(self) -> set[str]:
        return set(_KEY.findall(self.body)) | set(_KEY.findall(self.system))

    def render(self, ctx: dict[str, Any]) -> str:
        missing = self.required_keys - set(ctx)
        if missing:
            raise ValueError(f"{self.name} missing context keys: {sorted(missing)}")
        return _KEY.sub(lambda m: str(ctx[m.group(1)]), self.body)


def load_template(name: str) -> Template:
    tpl_path = PROMPT_DIR / f"{name}.toml"
    if not tpl_path.exists():
        raise FileNotFoundError(f"Prompt template {name}.toml not found in {PROMPT_DIR}")
    d = tomllib.loads(tpl_path.read_text(encoding="utf-8"))
    return Template(name=name, **d)


class _GenAiModelWrapper:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.last_model_used: str = ""
        self.last_latency_ms: float = 0.0

    def generate_content(self, model: str, contents: str, config: dict[str, Any] | None = None) -> Any:
        import urllib.request
        import urllib.error
        import json
        import time

        config = config or {}
        temperature = config.get("temperature", 0.3)
        system_inst = config.get("system_instruction")
        mime_type = config.get("response_mime_type")
        timeout_sec = config.get("timeout_sec", 60.0)

        try:
            from backend.app.core.config import settings
            fallback_cfg = settings.GEMINI_FALLBACK_MODELS
            timeout_sec = config.get("timeout_sec", settings.GEMINI_TIMEOUT_SEC)
        except Exception:
            fallback_cfg = os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash-lite,gemini-flash-lite-latest")

        verified = get_verified_gemini_models(self.api_key)
        candidate_models = build_failover_order(model, fallback_cfg, verified)
        if not candidate_models:
            candidate_models = [model, "gemini-3.5-flash-lite", "gemini-flash-lite-latest"]

        last_err = None
        has_rate_limit = False
        t_start = time.perf_counter()

        for candidate in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate}:generateContent?key={self.api_key}"
            payload: dict[str, Any] = {
                "contents": [{"parts": [{"text": str(contents)}]}],
                "generationConfig": {"temperature": temperature},
            }
            if mime_type:
                payload["generationConfig"]["response_mime_type"] = mime_type
            if system_inst:
                payload["system_instruction"] = {"parts": [{"text": str(system_inst)}]}

            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            # Try up to 2 attempts per candidate (helps with temporary 503 spikes)
            for attempt in range(2):
                try:
                    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        candidates = data.get("candidates", [])
                        if not candidates:
                            raise ValueError(f"No candidates returned by Gemini: {data}")
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        text = parts[0].get("text", "") if parts else ""
                        usage = data.get("usageMetadata", {})

                        self.last_model_used = candidate
                        self.last_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)

                        class GenAiResponse:
                            def __init__(self, t: str, u: dict, m: str):
                                self.text = t
                                self.model_name = m
                                self.usage_metadata = type(
                                    "Usage",
                                    (),
                                    {
                                        "prompt_token_count": u.get("promptTokenCount", 0),
                                        "candidates_token_count": u.get("candidatesTokenCount", 0),
                                    },
                                )()

                        return GenAiResponse(text, usage, candidate)
                except urllib.error.HTTPError as e:
                    err_text = e.read().decode("utf-8", errors="replace")
                    last_err = f"HTTP {e.code}: {err_text}"
                    if e.code == 429:
                        has_rate_limit = True
                    if e.code == 503 and attempt == 0:
                        time.sleep(0.6)
                        continue
                    if e.code in (404, 503, 429):
                        logger.warning("Gemini model '%s' returned %d, falling back to next candidate: %s", candidate, e.code, err_text[:120])
                        break
                    raise RuntimeError(last_err) from e
                except Exception as e:
                    last_err = str(e)
                    if attempt == 0:
                        time.sleep(0.5)
                        continue
                    break

        if has_rate_limit:
            raise GeminiRateLimitError(f"AI is busy, retry in about 1 minute (Last error: {last_err})")
        raise RuntimeError(f"All candidate models failed. Last error: {last_err}")


class GeminiRestClient:
    """Built-in lightweight REST client providing an identical interface to google.genai.Client."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.models = _GenAiModelWrapper(api_key)


class GeminiClient:
    """Manages Gemini calls with mandatory logging to ai_interactions table."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        session_factory: Any = None,
    ):
        try:
            from backend.app.core.config import settings
            default_key = settings.GEMINI_API_KEY
            default_model = settings.GEMINI_MODEL
        except Exception:
            default_key = os.getenv("GEMINI_API_KEY", "")
            default_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

        self._api_key = api_key or default_key or os.getenv("GEMINI_API_KEY", "")
        self._model_name = model_name or default_model or os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        self._sessions = session_factory
        self._client = None
        self.last_model_used: str = ""
        self.last_latency_sec: float = 0.0

        self._ensure_client()

    def _ensure_client(self) -> None:
        if self._client:
            return
        try:
            from backend.app.core.config import settings
            api_key = self._api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
            model_name = self._model_name or settings.GEMINI_MODEL or os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
        except Exception:
            api_key = self._api_key or os.getenv("GEMINI_API_KEY", "")
            model_name = self._model_name or os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

        if api_key and api_key not in ("your_gemini_api_key_here", ""):
            self._api_key = api_key
            self._model_name = model_name
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except Exception:
                # Built-in zero-dependency REST client
                self._client = GeminiRestClient(api_key=self._api_key)

    @property
    def is_configured(self) -> bool:
        self._ensure_client()
        return self._client is not None

    def call(self, template_name: str, ctx: dict[str, Any], *, user_id: int) -> str:
        self._ensure_client()
        tpl = load_template(template_name)
        prompt = tpl.render(ctx)
        effective_model = self._model_name or tpl.model

        if not self._client:
            logger.error(
                "Gemini API request rejected: client not configured or GEMINI_API_KEY is missing."
            )
            raise GeminiUnavailableError("AI assistant unavailable, retry")

        try:
            resp = self._client.models.generate_content(
                model=effective_model,
                contents=prompt,
                config={"system_instruction": tpl.system, "temperature": 0.4},
            )
            if hasattr(resp, "model_name") and resp.model_name:
                self.last_model_used = resp.model_name
            elif hasattr(self._client, "models") and hasattr(self._client.models, "last_model_used"):
                self.last_model_used = self._client.models.last_model_used
            response_text = resp.text or ""
            tokens_in = len(prompt.split()) * 2
            tokens_out = len(response_text.split()) * 2
            if hasattr(resp, "usage_metadata") and resp.usage_metadata:
                tokens_in = getattr(resp.usage_metadata, "prompt_token_count", tokens_in)
                tokens_out = getattr(resp.usage_metadata, "candidates_token_count", tokens_out)
        except GeminiRateLimitError:
            raise
        except Exception as e:
            logger.exception("Gemini API call failed for template '%s': %s", template_name, e)
            raise GeminiUnavailableError("AI assistant unavailable, retry") from e

        # Log every successful interaction to Table 26 (ai_interactions)
        self._log(user_id, tpl, prompt, response_text, tokens_in, tokens_out)
        return response_text

    def generate_structured_json(
        self,
        prompt: str,
        system_instruction: str = "",
        *,
        user_id: int | None = None,
        timeout_sec: float | None = None,
    ) -> str:
        """Calls Gemini with response_mime_type=application/json and an enforced timeout."""
        self._ensure_client()
        if not self._client:
            raise GeminiUnavailableError("Gemini client not configured")

        if timeout_sec is None:
            try:
                from backend.app.core.config import settings
                timeout_sec = settings.GEMINI_TIMEOUT_SEC
            except Exception:
                timeout_sec = 60.0

        effective_model = self._model_name or "gemini-3.5-flash"

        def _do_call():
            config = {
                "response_mime_type": "application/json",
                "temperature": 0.3,
                "timeout_sec": timeout_sec,
            }
            if system_instruction:
                config["system_instruction"] = system_instruction
            resp = self._client.models.generate_content(
                model=effective_model,
                contents=prompt,
                config=config,
            )
            if hasattr(resp, "model_name") and resp.model_name:
                self.last_model_used = resp.model_name
            elif hasattr(self._client, "models") and hasattr(self._client.models, "last_model_used"):
                self.last_model_used = self._client.models.last_model_used
            return resp.text or ""

        import concurrent.futures
        import time
        t0 = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_do_call)
            try:
                result_text = future.result(timeout=timeout_sec + 5.0)
                self.last_latency_sec = time.perf_counter() - t0
                return result_text
            except concurrent.futures.TimeoutError as e:
                logger.warning("Gemini structured JSON generation timed out after %.1fs", timeout_sec)
                raise GeminiUnavailableError("Gemini API call timed out") from e
            except GeminiRateLimitError:
                raise
            except Exception as e:
                logger.warning("Gemini structured JSON generation failed: %s", e)
                raise GeminiUnavailableError(f"Gemini call failed: {e}") from e


    def _log(
        self,
        user_id: int,
        tpl: Template,
        prompt: str,
        response_text: str,
        tokens_in: int,
        tokens_out: int,
    ) -> None:
        """Writes ai_interactions. Mandatory per Table 26 and research AI-usage disclosure."""
        if not self._sessions:
            return
        try:
            from backend.app.models.core import AiInteraction
            with self._sessions() as s:
                s.add(
                    AiInteraction(
                        user_id=user_id,
                        prompt_type=tpl.name,
                        prompt_version=tpl.version,
                        prompt_text=prompt,
                        response_text=response_text,
                        model_name=self._model_name or tpl.model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                    )
                )
                s.commit()
        except Exception:
            logger.exception("Failed to write ai_interaction log entry for user %s", user_id)
