---
name: anthropic-claude-api
description: >-
  Anthropic Claude API integration for the Data-Answers Agent frontier model
  tier. Use when implementing model_router.py reason(), classification prompts,
  or formatting grounded query results — never for generating SQL.
---

# Anthropic Claude API (Frontier Tier)

## Package

```toml
"anthropic>=0.40"
```

Env: `ANTHROPIC_API_KEY` — never commit.

## Model router seam

```python
import anthropic
from app.config import settings

class ModelRouter:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def classify(self, question: str) -> IntentResult:
        # Cheap tier: heuristic first; optional Haiku for classify
        ...

    def reason(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=settings.frontier_model,  # e.g. claude-sonnet-4-20250514
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
```

## Allowed uses

- Classify intent (is this a data question? in-scope?)
- Format grounded numeric results into natural language
- Generate clarification questions when ambiguous

## Forbidden uses

- **Generating SQL** from schema — violates grounding non-negotiable
- Answering from model knowledge without warehouse execution
- Bypassing policy gate or audit

## Prompt template for answer formatting

```
You are a business data assistant. Format the following grounded query result
into a clear answer for a non-technical user.

Question: {question}
Resolved interpretation: {interpretation}
Metric: {metric_id}
Result rows: {rows}

Rules:
- Do not mention SQL, tables, or column names
- State the answer clearly with units
- If data is insufficient, say so — do not invent numbers
```

## Cost control

- Track `response.usage.input_tokens + output_tokens` against `TOKEN_BUDGET`
- Prefer cheap tier / skip `reason()` when verified-query result is self-explanatory
- Cache hits skip the full loop entirely

## CI mocking

```python
class FakeAnthropic:
    def messages(self):
        return self
    def create(self, **kwargs):
        return type("R", (), {"content": [type("B", (), {"text": "mock"})()]})()
```

Never call live API in pytest.
