"""Evaluation harness models."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models import UserPrincipal


class GoldenExpectation(BaseModel):
    status: Literal["ok", "needs_clarification", "declined", "error"]
    source: Optional[str] = None
    audit_metric_id: Optional[str] = None
    audit_grounding_status: Optional[str] = None
    audit_policy_decision: Optional[str] = None
    answer_must_not_contain: list[str] = Field(default_factory=list)


class GoldenCase(BaseModel):
    id: str
    description: str
    question: str
    user_principal: UserPrincipal
    expect: GoldenExpectation


class GoldenSet(BaseModel):
    cases: list[GoldenCase]


class CaseResult(BaseModel):
    case_id: str
    passed: bool
    expected_status: str
    actual_status: str
    failures: list[str] = Field(default_factory=list)
    request_id: Optional[str] = None


class EvalReport(BaseModel):
    total: int
    passed: int
    failed: int
    deflection_rate: float
    clarification_rate: float
    decline_rate: float
    cases: list[CaseResult]

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0
