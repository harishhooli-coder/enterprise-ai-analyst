"""NVIDIA NIM chat completions (OpenAI-compatible API)."""

from __future__ import annotations

import httpx

from app.config import get_settings


class NimApiError(Exception):
    """Raised when the NIM API returns an error response."""


def chat_completion(prompt: str, *, model: str | None = None, max_tokens: int = 1024) -> str:
    settings = get_settings()
    api_key = settings.nim_api_key
    if not api_key:
        raise RuntimeError("NIM_API_KEY is not configured")

    base_url = settings.nim_base_url.rstrip("/")
    model_id = model or settings.nim_model

    response = httpx.post(
        f"{base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
            "top_p": 0.9,
        },
        timeout=120.0,
    )

    if response.status_code >= 400:
        raise NimApiError(f"NIM API error {response.status_code}: {response.text[:300]}")

    payload = response.json()
    try:
        return payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise NimApiError(f"Unexpected NIM response shape: {payload!r}") from exc
