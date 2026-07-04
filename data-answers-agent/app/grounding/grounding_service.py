"""Load registry at startup and resolve questions to grounded metric templates."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from app.config import get_settings
from app.grounding.retrieval import KeywordRetriever, MetricRetriever, select_retriever
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


def extract_month(question: str) -> str | None:
    """Extract a calendar month (YYYY-MM) from natural-language text."""
    normalized = re.sub(r"\s+", " ", question.strip().lower())

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


def _metric_by_id(registry: list[dict[str, Any]], metric_id: str) -> dict[str, Any] | None:
    return next((item for item in registry if item["id"] == metric_id), None)


def _keyword_tied_candidates(
    keyword_ranked: list,
    registry: list[dict[str, Any]],
) -> list[str] | None:
    if len(keyword_ranked) < 2 or keyword_ranked[0].score != keyword_ranked[1].score:
        return None
    top_metrics = [
        _metric_by_id(registry, item.metric_id) for item in keyword_ranked[:2]
    ]
    groups = {
        (metric.get("ambiguity_group") or metric["id"])
        for metric in top_metrics
        if metric is not None
    }
    if len(groups) == 1:
        return [item.metric_id for item in keyword_ranked[:2]]
    return None


class GroundingService:
    """Resolve questions via keyword or embedding retrieval over the flat registry."""

    def __init__(
        self,
        retriever: MetricRetriever | None = None,
        *,
        registry: list[dict[str, Any]] | None = None,
    ) -> None:
        self._registry = registry if registry is not None else _load_registry()
        self._retriever = retriever
        self._keyword_fallback = KeywordRetriever()

    @property
    def registry(self) -> list[dict[str, Any]]:
        return list(self._registry)

    def _get_retriever(self) -> MetricRetriever:
        if self._retriever is not None:
            return self._retriever
        settings = get_settings()
        return select_retriever(settings.grounding_retrieval)

    def resolve(self, question: str) -> GroundingResult:
        settings = get_settings()
        keyword_ranked = self._keyword_fallback.rank(question, self._registry)

        tied = _keyword_tied_candidates(keyword_ranked, self._registry)
        if tied is not None:
            return GroundingResult(
                status="ambiguous",
                candidates=tied,
                clarify_prompt=_build_clarify_prompt(tied, self._registry),
            )

        retriever = self._get_retriever()
        ranked = retriever.rank(question, self._registry)

        if not ranked:
            return self._resolve_from_keyword(keyword_ranked, question)

        top = ranked[0]
        top_metric = _metric_by_id(self._registry, top.metric_id)
        has_keyword_overlap = bool(keyword_ranked and keyword_ranked[0].metric_id == top.metric_id)

        required_score = settings.embedding_match_threshold
        if not has_keyword_overlap:
            required_score += 0.15

        if top.score < required_score:
            return self._resolve_from_keyword(keyword_ranked, question)

        if len(ranked) > 1:
            second = ranked[1]
            if (
                second.score >= settings.embedding_match_threshold
                and top.score - second.score < settings.embedding_ambiguity_margin
            ):
                top_metrics = [
                    _metric_by_id(self._registry, item.metric_id)
                    for item in ranked[:2]
                ]
                groups = {
                    (metric.get("ambiguity_group") or metric["id"])
                    for metric in top_metrics
                    if metric is not None
                }
                if len(groups) == 1:
                    candidate_ids = [item.metric_id for item in ranked[:2]]
                    return GroundingResult(
                        status="ambiguous",
                        candidates=candidate_ids,
                        clarify_prompt=_build_clarify_prompt(candidate_ids, self._registry),
                    )

        if top_metric is None:
            return GroundingResult(status="out_of_set")

        return self._build_match(top_metric, question)

    def _resolve_from_keyword(self, keyword_ranked: list, question: str) -> GroundingResult:
        if not keyword_ranked:
            return GroundingResult(status="out_of_set")
        metric = _metric_by_id(self._registry, keyword_ranked[0].metric_id)
        if metric is None:
            return GroundingResult(status="out_of_set")
        return self._build_match(metric, question)

    def _build_match(self, metric: dict[str, Any], question: str) -> GroundingResult:
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


def resolve(question: str) -> GroundingResult:
    """Resolve a question using the module-level registry loaded at startup."""
    return grounding_service.resolve(question)


# Registry loaded once at import time (startup for the skeleton).
# TODO(harden): back registry with dbt Semantic Layer or Cube; add join-path graph reasoning
grounding_service = GroundingService()
