"""Pydantic v2 models shared across API, loop, grounding, policy, and tools."""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class UserPrincipal(BaseModel):
    user_id: str
    allowed_regions: list[str]


class AskRequest(BaseModel):
    question: str
    user_principal: UserPrincipal


class AnswerPayload(BaseModel):
    answer: str
    resolved_interpretation: str
    source: str
    confidence: float = Field(ge=0.0, le=1.0)


class IntentResult(BaseModel):
    intent: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class AllowDeny(BaseModel):
    allowed: bool
    reason: str


class GroundingResult(BaseModel):
    status: Literal["match", "ambiguous", "out_of_set"]
    metric_id: Optional[str] = None
    template: Optional[str] = None
    resolved_params: Optional[dict[str, str]] = None
    candidates: Optional[list[str]] = None
    clarify_prompt: Optional[str] = None


class ScanResult(BaseModel):
    flagged: bool
    reason: Optional[str] = None


class QueryParameterDef(BaseModel):
    name: str
    type: str
    description: Optional[str] = None


class VerifiedQueryTemplate(BaseModel):
    id: str
    sql: str
    parameters: list[QueryParameterDef] = Field(default_factory=list)


class MetricDef(BaseModel):
    id: str
    name: str
    description: str
    aliases: list[str] = Field(default_factory=list)
    template: str
    parameters: list[QueryParameterDef] = Field(default_factory=list)
    ambiguity_group: Optional[str] = None


class WarehouseResult(BaseModel):
    rows: list[dict]
    bytes_scanned: int
    template_id: str
