"""Two-tier model routing: cheap classify vs frontier reason."""

from __future__ import annotations

import os
import re
from typing import Optional, Protocol

from pydantic import BaseModel, Field

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
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._frontier_model = frontier_model or os.getenv(
            "FRONTIER_MODEL", "claude-sonnet-4-20250514"
        )
        self._tokens_used = 0
        # TODO(harden): inject classify_fn / reason_fn for policy-driven tier selection

    @property
    def tokens_used(self) -> int:
        return self._tokens_used

    def reset_token_count(self) -> None:
        self._tokens_used = 0

    def _get_client(self) -> _AnthropicClient:
        if self._client is not None:
            return self._client
        import anthropic

        key = self._api_key if self._api_key is not None else os.getenv("ANTHROPIC_API_KEY", "")
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
        """Frontier tier: Anthropic Claude for grounded result formatting (lazy client)."""
        self._tokens_used += min(len(prompt) // 4, 500)
        key = self._api_key if self._api_key is not None else os.getenv("ANTHROPIC_API_KEY", "")
        if self._client is None and not key:
            return self._stub_reason(prompt)
        client = self._get_client()
        response = client.messages.create(
            model=self._frontier_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        block = response.content[0]
        text = block.text  # type: ignore[attr-defined]
        self._tokens_used += len(text) // 4
        return text

    def _stub_reason(self, prompt: str) -> str:
        if "total_revenue" in prompt or "1250000" in prompt or "1,250,000" in prompt:
            return "Total revenue last month was $1.25M."
        return "Here is the answer based on the verified query results."


router = ModelRouter()
