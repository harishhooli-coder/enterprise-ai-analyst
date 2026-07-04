"""Evaluation harness — golden-set offline trust metrics."""

from app.eval.harness import load_golden_set, run_golden_eval
from app.eval.models import CaseResult, EvalReport, GoldenCase, GoldenSet

__all__ = [
    "CaseResult",
    "EvalReport",
    "GoldenCase",
    "GoldenSet",
    "load_golden_set",
    "run_golden_eval",
]
