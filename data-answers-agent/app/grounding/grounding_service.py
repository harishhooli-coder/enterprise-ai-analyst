"""Load registry at startup and resolve questions to grounded metric templates."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings
from app.models import GroundingResult

_REGISTRY_PATH = Path(__file__).parent / "registry.yaml"
_MONTH_NAME_PATTERN = (
    r"\b(january|february|march|april|may|june|july|august|"
    r"september|october|november|december)\s+(\d{4})\b"
)
_MONTH_NAMES = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def _load_registry() -> list[dict[str, Any]]:
    with _REGISTRY_PATH.open(encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return payload.get("metrics", [])


def _normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", question.strip().lower())


def _match_terms(metric: dict[str, Any]) -> list[str]:
    terms = [metric.get("name", ""), metric.get("id", "").replace("_", " ")]
    terms.extend(metric.get("aliases", []))
    return [term.strip().lower() for term in terms if term.strip()]


def _best_alias_match_length(normalized_question: str, metric: dict[str, Any]) -> int:
    best = 0
    for term in _match_terms(metric):
        if term in normalized_question:
            best = max(best, len(term))
    return best


def extract_month(question: str) -> str | None:
    """Extract a calendar month (YYYY-MM) from natural-language text."""
    normalized = _normalize_question(question)

    if re.search(r"\blast\s+month\b", normalized):
        return _shift_month(date.today(), -1)
    if re.search(r"\bthis\s+month\b", normalized):
        return _format_month(date.today())

    iso_match = re.search(r"\b(\d{4})-(\d{2})\b", normalized)
    if iso_match:
        year, month = int(iso_match.group(1)), int(iso_match.group(2))
        if 1 <= month <= 12:
            return f"{year:04d}-{month:02d}"

    named_match = re.search(_MONTH_NAME_PATTERN, normalized)
    if named_match:
        month_num = _MONTH_NAMES[named_match.group(1)]
        year = int(named_match.group(2))
        return f"{year:04d}-{month_num:02d}"

    return None


def _shift_month(today: date, delta_months: int) -> str:
    month_index = today.year * 12 + (today.month - 1) + delta_months
    year, zero_based_month = divmod(month_index, 12)
    return f"{year:04d}-{zero_based_month + 1:02d}"


def _format_month(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def _requires_question_param(metric: dict[str, Any], param_name: str) -> bool:
    for param in metric.get("parameters", []):
        if (
            param.get("name") == param_name
            and param.get("required", True)
            and param.get("resolved_by") != "warehouse"
        ):
            return True
    return False


def _build_clarify_prompt(candidate_ids: list[str], registry: list[dict[str, Any]]) -> str:
    names: list[str] = []
    for candidate_id in candidate_ids:
        metric = next((item for item in registry if item["id"] == candidate_id), None)
        if metric:
            names.append(metric["name"])
    if len(names) >= 2:
        return (
            f"Your question could refer to more than one metric. "
            f"Did you mean {', '.join(names[:-1])}, or {names[-1]}?"
        )
    return "Your question matches multiple metrics. Please clarify which one you mean."


def _format_template(template: str) -> str:
    settings = get_settings()
    return (
        template.replace("{project}", settings.bq_project_id).replace(
            "{dataset}", settings.bq_dataset
        )
    )


class GroundingService:
    """Simple keyword/alias matcher over the flat metric registry."""

    def __init__(self) -> None:
        self._registry = _load_registry()

    @property
    def registry(self) -> list[dict[str, Any]]:
        return list(self._registry)

    def resolve(self, question: str) -> GroundingResult:
        normalized = _normalize_question(question)
        matches = self._find_matching_metrics(normalized)

        if not matches:
            return GroundingResult(status="out_of_set")

        if len(matches) > 1:
            groups = {metric.get("ambiguity_group") or metric["id"] for metric in matches}
            if len(groups) == 1:
                candidate_ids = [metric["id"] for metric in matches]
                return GroundingResult(
                    status="ambiguous",
                    candidates=candidate_ids,
                    clarify_prompt=_build_clarify_prompt(candidate_ids, self._registry),
                )

        metric = matches[0]
        month = extract_month(question)
        resolved_params: dict[str, str] = {}
        if month is not None and _requires_question_param(metric, "month"):
            resolved_params["month"] = month

        template = _format_template(metric["template"])

        if month is None and _requires_question_param(metric, "month"):
            return GroundingResult(
                status="match",
                metric_id=metric["id"],
                template=template,
                resolved_params=resolved_params or None,
                clarify_prompt=(
                    "Which calendar month should I use? "
                    "For example, you can say 'last month' or '2026-03'."
                ),
            )

        return GroundingResult(
            status="match",
            metric_id=metric["id"],
            template=template,
            resolved_params=resolved_params or None,
        )

    def _find_matching_metrics(self, normalized_question: str) -> list[dict[str, Any]]:
        matched: list[tuple[int, dict[str, Any]]] = []
        for metric in self._registry:
            match_length = _best_alias_match_length(normalized_question, metric)
            if match_length > 0:
                matched.append((match_length, metric))

        if not matched:
            return []

        max_length = max(length for length, _ in matched)
        return [metric for length, metric in matched if length == max_length]


def resolve(question: str) -> GroundingResult:
    """Resolve a question using the module-level registry loaded at startup."""
    return grounding_service.resolve(question)


# Registry loaded once at import time (startup for the skeleton).
# TODO(harden): back registry with dbt Semantic Layer or Cube; add embedding retrieval
grounding_service = GroundingService()
