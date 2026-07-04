---
name: agent-orchestration
description: >-
  Bounded agent orchestration loop, two-tier model routing, policy gate PEP/PDP,
  and guardrails for the Data-Answers Agent. Use when implementing orchestrator.py,
  model_router.py, gate.py, guardrails.py, or audit.py.
---

# Agent Orchestration

## Loop (orchestrator.py)

Bounded plan→resolve→authorize→execute→answer. Hard step cap + token/cost budget.

```
1. audit.open + guardrails.scan_input(question)
2. model_router.classify(question) → intent
3. grounding_service.resolve(question) → MATCH | AMBIGUOUS | OUT_OF_SET
   - AMBIGUOUS → ApiResponse(needs_clarification)
   - OUT_OF_SET  → ApiResponse(declined)
4. policy.authorize(principal, resource=metric_id, metadata) → allow | deny
   - deny → declined + audited
5. tools.query_warehouse(template, params, principal)
6. model_router.reason (optional) → format answer from rows
7. guardrails.redact_output → AnswerPayload
8. audit.close → ApiResponse(ok)
```

Enforce caps:

```python
MAX_STEPS = 10  # from config
TOKEN_BUDGET = 8000  # abort → status=error, audited
```

## Model router (two-tier)

```python
class ModelRouter:
    def classify(self, question: str) -> IntentResult: ...   # cheap tier
    def reason(self, prompt: str) -> str: ...                 # frontier (Claude)
```

- Cheap tier: heuristics, regex, or fast/local model — mockable in CI
- Frontier tier: Anthropic API via env `ANTHROPIC_API_KEY`
- **Never** use frontier tier to generate SQL — only to format grounded results or classify

Routing policy lives in one file so it is swappable.

## Policy gate (PEP→PDP)

Every tool call passes through `authorize()` before execution:

```python
class AllowDeny(BaseModel):
    allowed: bool
    reason: str

def authorize(
    principal: UserPrincipal,
    resource: str,       # metric_id or tool name
    metadata: dict,
) -> AllowDeny:
    if not principal.allowed_regions:
        return AllowDeny(allowed=False, reason="no_allowed_regions")
    return AllowDeny(allowed=True, reason="skeleton_allow")
```

Log every decision to audit. No tool bypasses the gate.

```python
# TODO(harden): replace with OPA/Rego or warehouse-native policy
```

## Guardrails

```python
def scan_input(question: str) -> ScanResult:
    # Flag injection markers, secret patterns (sk stub → presidio later)
    ...

def redact_output(payload: AnswerPayload) -> AnswerPayload:
    # Strip leaked SQL, table names, PII from user-facing answer
    ...
```

Must be on the request path — not dead code.

## Audit (reconstructable record)

One record per request:

```python
{
  "request_id": "...",
  "timestamp": "...",
  "principal": {"user_id": "...", "allowed_regions": [...]},
  "question": "...",
  "grounding_status": "match|ambiguous|out_of_set",
  "metric_id": "...",
  "policy_decision": "allow|deny",
  "bytes_scanned": 0,
  "latency_ms": 0,
  "response_status": "ok|needs_clarification|declined|error",
}
```

Use **structlog** JSON to stdout in skeleton; `# TODO(harden): OpenTelemetry span export`.

## Behaviour contract

| Situation | Response |
|-----------|----------|
| Grounded match + policy allow + query ok | `ok` + provenance + confidence |
| Ambiguous metric | `needs_clarification` + specific question |
| Out of scope | `declined` + "routed to human" |
| Policy deny | `declined` + audited reason |
| Budget/step exceeded | `error` + audited |
