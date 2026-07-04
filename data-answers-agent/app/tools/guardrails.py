"""Input scan and output redaction guardrails (skeleton regex stubs)."""

from __future__ import annotations

import re

from app.models import AnswerPayload, ScanResult

# TODO(harden): expand rule catalog; wire Presidio; add rebuff/Lakera if needed

INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.I),
    re.compile(r"system\s*:", re.I),
    re.compile(r"```\s*sql", re.I),
    re.compile(r";\s*drop\s+table", re.I),
]

SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (RSA |)PRIVATE KEY-----"),
]

SCHEMA_LEAK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"`[\w-]+\.[\w-]+\.[\w-]+`", re.I),
    re.compile(r"\b[a-z_]+\.[a-z_]+\.[a-z_]+\b", re.I),
    re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|FROM|WHERE|JOIN)\b", re.I),
]


def scan_input(question: str) -> ScanResult:
    """Flag injection markers or embedded secrets in the user question."""
    for pattern in INJECTION_PATTERNS:
        if pattern.search(question):
            return ScanResult(flagged=True, reason="injection_pattern_detected")

    for pattern in SECRET_PATTERNS:
        if pattern.search(question):
            return ScanResult(flagged=True, reason="secret_pattern_detected")

    return ScanResult(flagged=False, reason=None)


def redact_output(payload: AnswerPayload) -> AnswerPayload:
    """Strip leaked SQL, schema references, and table names from the user-facing answer."""
    redacted = payload.answer
    for pattern in SCHEMA_LEAK_PATTERNS:
        redacted = pattern.sub("[redacted]", redacted)

    if redacted != payload.answer:
        return payload.model_copy(update={"answer": redacted})
    return payload
