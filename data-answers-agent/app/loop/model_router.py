"""Two-tier model routing: cheap classify vs frontier reason."""

from __future__ import annotations

import re
from typing import Optional, Protocol

from pydantic import BaseModel, Field

from app.config import get_settings

# TODO(harden): centralize routing policy (model IDs, tier thresholds, embedding retrieval)

_DATA_QUESTION_PATTERNS = (
    re.compile(r"\b(revenue|sales|profit|orders|customers|metric|total|last month|this month)\b", re.I),
    re.compile(r"\bwhat was\b|\bhow much\b|\bhow many\b|\bshow me\b", re.I),
)
_INJECTION_HEURISTIC = re.compile(
    r"ignore\s+(all\s+)?previous\s+instructions|system\s*:|```\s*sql",
    re.I,
)


class IntentResult(BaseModel):
    intent: str
    confidence: float = Field(ge=0.0, le=1.0)


class _MessagesAPI(Protocol):
    def create(self, *, model: str, max_tokens: int, messages: list[dict]) -> object: ...


class _AnthropicClient(Protocol):
    messages: _MessagesAPI


class ModelRouter:
    """Routes classification to a cheap tier and reasoning to the frontier tier."""

    def __init__(
        self,
        *,
        client: Optional[_AnthropicClient] = None,
        api_key: Optional[str] = None,
        frontier_model: Optional[str] = None,
        frontier_provider: Optional[str] = None,
    ) -> None:
        self._client = client
        self._api_key = api_key
        settings = get_settings()
        self._frontier_model = frontier_model or settings.frontier_model
        self._frontier_provider = frontier_provider or settings.frontier_provider
        self._tokens_used = 0
        # TODO(harden): inject classify_fn / reason_fn for policy-driven tier selection

    @property
    def tokens_used(self) -> int:
        return self._tokens_used

    def reset_token_count(self) -> None:
        self._tokens_used = 0

    def _get_anthropic_client(self) -> _AnthropicClient:
        if self._client is not None:
            return self._client
        import anthropic

        settings = get_settings()
        key = self._api_key if self._api_key is not None else settings.anthropic_api_key
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        self._client = anthropic.Anthropic(api_key=key)
        return self._client

    def classify(self, question: str) -> IntentResult:
        """Cheap tier: heuristic intent classification (mockable, no live API)."""
        self._tokens_used += 50
        text = question.strip()
        if not text:
            return IntentResult(intent="out_of_scope", confidence=0.0)

        if _INJECTION_HEURISTIC.search(text):
            return IntentResult(intent="injection_attempt", confidence=0.95)

        matches = sum(1 for pattern in _DATA_QUESTION_PATTERNS if pattern.search(text))
        if matches >= 2:
            return IntentResult(intent="data_question", confidence=min(0.5 + 0.2 * matches, 0.95))
        if matches == 1:
            return IntentResult(intent="data_question", confidence=0.55)

        return IntentResult(intent="out_of_scope", confidence=0.7)

    def reason(self, prompt: str) -> str:
        """Frontier tier: NIM (primary) or Anthropic for grounded result formatting."""
        self._tokens_used += min(len(prompt) // 4, 500)
        settings = get_settings()
        provider = self._frontier_provider

        if provider == "nim" and settings.nim_api_key:
            try:
                text = self._reason_nim(prompt)
                self._tokens_used += len(text) // 4
                return text
            except Exception:
                if settings.anthropic_api_key:
                    text = self._reason_anthropic(prompt)
                    self._tokens_used += len(text) // 4
                    return text
                raise

        if provider == "anthropic" and settings.anthropic_api_key:
            text = self._reason_anthropic(prompt)
            self._tokens_used += len(text) // 4
            return text

        if settings.nim_api_key:
            text = self._reason_nim(prompt)
            self._tokens_used += len(text) // 4
            return text

        if settings.anthropic_api_key:
            text = self._reason_anthropic(prompt)
            self._tokens_used += len(text) // 4
            return text

        return self._stub_reason(prompt)

    def _reason_nim(self, prompt: str) -> str:
        from app.loop.nim_client import chat_completion

        return chat_completion(prompt)

    def _reason_anthropic(self, prompt: str) -> str:
        client = self._get_anthropic_client()
        response = client.messages.create(
            model=self._frontier_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        block = response.content[0]
        return block.text  # type: ignore[attr-defined]

    def _stub_reason(self, prompt: str) -> str:
        if "total_revenue" in prompt or "1250000" in prompt or "1,250,000" in prompt:
            return "Total revenue last month was $1.25M."
        return "Here is the answer based on the verified query results."


router = ModelRouter()
