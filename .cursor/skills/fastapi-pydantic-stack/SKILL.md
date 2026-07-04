---
name: fastapi-pydantic-stack
description: >-
  FastAPI + Pydantic v2 patterns for the Data-Answers Agent API layer.
  Use when creating routes, ApiResponse envelopes, AskRequest models, config.py,
  or pyproject.toml for this project's FastAPI service.
---

# FastAPI + Pydantic Stack

## Stack defaults

- **FastAPI** + **Uvicorn** for HTTP
- **Pydantic v2** for all request/response models
- **pydantic-settings** or **python-dotenv** for env config
- **httpx** + FastAPI `TestClient` for tests

## pyproject.toml essentials

```toml
[project]
name = "data-answers-agent"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "pydantic>=2.0",
  "pydantic-settings>=2.0",
  "python-dotenv>=1.0",
  "pyyaml>=6.0",
  "structlog>=24.0",
  "google-cloud-bigquery>=3.0",
  "anthropic>=0.40",
  "httpx>=0.27",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.24", "ruff>=0.8", "mypy>=1.13"]
```

## ApiResponse envelope (exact shape)

```python
from typing import Generic, Literal, Optional, TypeVar
from pydantic import BaseModel, Field
import uuid

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    status: Literal["ok", "needs_clarification", "declined", "error"]
    data: Optional[T] = None
    clarification: Optional[str] = None
    decline_reason: Optional[str] = None
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    error: Optional[str] = None
```

## Core models

```python
class UserPrincipal(BaseModel):
    user_id: str
    allowed_regions: list[str]

class AskRequest(BaseModel):
    question: str
    user_principal: UserPrincipal

class AnswerPayload(BaseModel):
    answer: str
    resolved_interpretation: str
    source: str          # metric or verified-query id
    confidence: float    # 0..1
```

## Route pattern

```python
@app.post("/ask", response_model=ApiResponse[AnswerPayload])
async def ask(body: AskRequest) -> ApiResponse[AnswerPayload]:
    request_id = str(uuid.uuid4())
    audit.open(request_id, body.user_principal, body.question)
    try:
        result = await orchestrator.handle(body, request_id)
        audit.close(request_id, result)
        return result
    except Exception as exc:
        audit.error(request_id, exc)
        return ApiResponse(status="error", error=str(exc), request_id=request_id)
```

## config.py pattern

- Load from env; never hardcode project IDs, dataset names, or secrets
- Required vars: `ANTHROPIC_API_KEY`, `BQ_PROJECT_ID`, `BQ_DATASET`, `MAX_BYTES_BILLED`
- Optional: `LOG_LEVEL`, `AGENT_STEP_CAP`, `TOKEN_BUDGET`

## Rules

- Every route returns `ApiResponse<T>` — no bare dicts
- Validate input at the boundary; orchestrator receives typed models
- Use dependency injection for config, audit, orchestrator in tests
- No CORS/auth middleware in skeleton — accept principal in request body
