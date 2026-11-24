"""Minimal client for a *local* Ollama server."""
from __future__ import annotations

import json
import time

import httpx

from ..config import settings


class OllamaError(RuntimeError):
    code = "ollama_error"


class OllamaUnavailable(OllamaError):
    code = "ollama_unavailable"


class ModelMissing(OllamaError):
    code = "model_missing"


class OllamaTimeout(OllamaError):
    code = "ollama_timeout"


class OllamaBadResponse(OllamaError):
    code = "ollama_bad_response"


def check(timeout: float = 3.0) -> dict:
    """Return reachability and model availability without raising."""
    out = {"reachable": False, "model": settings.ollama_model, "model_available": False, "models": [],
           "url": settings.ollama_url, "error": None}
    try:
        r = httpx.get(f"{settings.ollama_url}/api/tags", timeout=timeout)
        r.raise_for_status()
        names = [m.get("name", "") for m in r.json().get("models", [])]
        out["reachable"] = True
        out["models"] = names
        want = settings.ollama_model
        out["model_available"] = any(n == want or n == f"{want}:latest" or n.split(":")[0] == want for n in names) \
            if ":" not in want else want in names
    except Exception as exc:  # noqa: BLE001
        out["error"] = f"{type(exc).__name__}: {exc}"[:300]
    return out


def chat(messages: list[dict], schema: dict | None = None, timeout: float | None = None,
         model: str | None = None) -> tuple[str, dict]:
    """Send a non-streaming chat request. Returns (content, stats)."""
    model = model or settings.ollama_model
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "format": schema or "json",
        "keep_alive": "30m",
        "options": {"temperature": 0.1, "num_ctx": 4096, "num_predict": 600, "seed": 7},
    }
    t0 = time.monotonic()
    try:
        r = httpx.post(f"{settings.ollama_url}/api/chat", json=payload,
                       timeout=httpx.Timeout(timeout or settings.ollama_timeout, connect=5.0))
    except httpx.ConnectError as exc:
        raise OllamaUnavailable(f"Cannot connect to Ollama at {settings.ollama_url} - is `ollama serve` running?") from exc
    except httpx.TimeoutException as exc:
        raise OllamaTimeout(f"Ollama did not answer within {timeout or settings.ollama_timeout:.0f}s") from exc
    except httpx.HTTPError as exc:
        raise OllamaUnavailable(f"Ollama request failed: {exc}") from exc

    if r.status_code == 404:
        raise ModelMissing(f"Model '{model}' is not available in Ollama. Run: ollama pull {model}")
    if r.status_code >= 400:
        raise OllamaBadResponse(f"Ollama returned HTTP {r.status_code}: {r.text[:300]}")
    try:
        body = r.json()
        content = body["message"]["content"]
    except (ValueError, KeyError, TypeError) as exc:
        raise OllamaBadResponse(f"Unexpected Ollama response: {r.text[:300]}") from exc
    stats = {
        "elapsed_ms": int((time.monotonic() - t0) * 1000),
        "prompt_tokens": body.get("prompt_eval_count"),
        "output_tokens": body.get("eval_count"),
        "model": body.get("model", model),
    }
    return content, stats


def parse_json_object(text: str) -> dict:
    """Parse the model output as a JSON object (tolerates surrounding text)."""
    text = (text or "").strip()
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            raise OllamaBadResponse("Model output is not valid JSON")
        try:
            obj = json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise OllamaBadResponse(f"Model output is not valid JSON: {exc}") from exc
    if not isinstance(obj, dict):
        raise OllamaBadResponse("Model output is not a JSON object")
    return obj
