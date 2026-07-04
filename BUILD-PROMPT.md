# BUILD-PROMPT.md — paste into Cursor Composer to scaffold the v1 walking skeleton

> Paste the whole of this into Cursor Composer (Agent mode). It assumes `.cursorrules` is in the repo root and in
> context. Build in the order given. After each numbered stage, STOP, show me the diff, and wait for "continue"
> before the next stage. Do not build ahead.

## Mission for this session
Scaffold a **walking skeleton**: a business user asks ONE grounded question ("What was total revenue last month?"),
for ONE user, and gets a trustworthy answer with provenance — running end-to-end through every architectural layer,
each layer thin but real. Prove the *shape* of the system, not its breadth.

The skeleton is a success when: `POST /ask` with a natural-language question + a user principal returns an
`ApiResponse` containing either (a) an answer with provenance/confidence, (b) a clarification request, or
(c) a decline — and every one of those paths is logged to the audit sink, with the query having run read-only and
bytes-capped through a policy gate that saw the user's identity.

## Scope fence (do NOT build these — leave TODOs)
- No artifacts/RAG server. No multi-source joins. No Postgres. No real dbt/Cube. No multi-tenancy.
- No real BigQuery RLS yet (use the stubbed row-filter per `.cursorrules`). No real MCP transport (typed tool
  functions stand in). No UI. No auth provider integration (accept a principal in the request for now).

## Target project structure
```
data-answers-agent/
  app/
    main.py                  # FastAPI app, /ask route
    envelope.py              # ApiResponse<T> model + helpers
    models.py                # Pydantic: AskRequest, UserPrincipal, AnswerPayload, etc.
    loop/
      orchestrator.py        # the bounded plan→resolve→authorize→execute→answer loop
      model_router.py        # two-tier routing (cheap classify vs frontier reason)
    grounding/
      registry.yaml          # metric defs + verified-query templates (the semantic layer stand-in)
      grounding_service.py    # load registry, match question→metric/template, ambiguity detection
    policy/
      gate.py                # PEP→PDP: authorize(principal, resource, metadata) -> allow/deny
    tools/
      warehouse.py           # query_warehouse(): read-only, parameterized, bytes-capped, runs AS principal (stub)
      guardrails.py          # input scan + output redaction (stubs, wired into the path)
    audit/
      audit.py               # structured audit logger; one record per request, reconstructable
    config.py                # env-driven config; no hardcoded secrets/ids
  tests/
    test_happy_path.py
    test_clarification.py
    test_decline.py
    test_readonly_guard.py
  .env.example
  pyproject.toml
  README.md
```

## The ApiResponse envelope (use exactly this shape)
```python
# every route returns this. T is the payload type.
class ApiResponse(BaseModel, Generic[T]):
    status: Literal["ok", "needs_clarification", "declined", "error"]
    data: Optional[T] = None
    # present when status == ok
    # (payload carries answer + provenance + confidence — see AnswerPayload)
    clarification: Optional[str] = None      # present when needs_clarification
    decline_reason: Optional[str] = None      # present when declined
    request_id: str                            # ties to the audit record
    error: Optional[str] = None
```
```python
class AnswerPayload(BaseModel):
    answer: str                    # the human-readable answer, no SQL/schema leaked
    resolved_interpretation: str   # what question we believed we answered
    source: str                    # the metric id or verified-query id it came from
    confidence: float              # 0..1, legible signal
```

## Build order (STOP after each; show diff; wait for "continue")

### Stage 1 — Skeleton bones + envelope + models + config + audit
- FastAPI app with `POST /ask` that accepts `AskRequest { question: str, user_principal: UserPrincipal }`.
- `UserPrincipal { user_id: str, allowed_regions: list[str] }` (the stub attributes RLS will later use).
- Wire the audit logger so EVERY request writes one structured record (request_id, principal, timestamp) even before
  logic exists. Return a hardcoded `ApiResponse(status="ok", ...)` for now to prove the pipe.
- `.env.example`, `config.py` (env-driven), `pyproject.toml`, README stub.
- Test: `POST /ask` returns 200 with a valid envelope and writes exactly one audit record.

### Stage 2 — Grounding registry + grounding service
- `registry.yaml` with 2–3 metrics/verified-query templates. Include at least: `total_revenue` (a parameterized,
  read-only SQL template with a `{month}` and a `{region_filter}` slot) and one metric that shares a word with
  another to force an ambiguity case (e.g. "revenue" vs "net revenue").
- `grounding_service.py`: load the registry; given a question, return one of: MATCH (a template + resolved params),
  AMBIGUOUS (>1 plausible metric), or OUT_OF_SET (no match). Retrieval can be simple keyword/cosine over the
  registry for now.
- Test: the ambiguity case returns AMBIGUOUS; an unknown question returns OUT_OF_SET.

### Stage 3 — Model router (two-tier)
- `model_router.py` exposing `classify(question) -> intent` (cheap tier) and `reason(prompt) -> text` (frontier tier,
  Claude). Behind one interface so routing policy is swappable. Skeleton may stub the cheap tier with a fast model or
  a heuristic, but the SEAM must be real. Frontier calls use the Anthropic API from env config.
- Test: classify routes to cheap tier, reason routes to frontier; both mockable in tests (no live API in CI).

### Stage 4 — Policy gate (PEP→PDP)
- `gate.py`: `authorize(principal, resource, metadata) -> AllowDeny`. Skeleton policy can be simple (e.g. allow if
  principal has ≥1 allowed_region) BUT it must be a real function every tool call passes through, and it must log its
  decision to audit. No tool call bypasses it.
- Test: a principal with no allowed_regions is denied and the denial is audited.

### Stage 5 — Warehouse tool (read-only, bytes-capped, identity-aware stub)
- `warehouse.py`: `query_warehouse(template, params, principal) -> rows`. Requirements:
  - Executes ONLY the parameterized template (no string-concatenated user text).
  - Injects the stub row-filter derived from `principal.allowed_regions` as the RLS stand-in.
  - Sets `maximum_bytes_billed`. Uses a read-only path. Rejects any template containing a write verb (guard function).
  - Leave `# TODO(harden): replace stub row-filter with BigQuery RLS via WIF/impersonation`.
  - In CI/skeleton, BigQuery may be mocked; the guards and the identity threading must be exercised by tests.
- Test: `test_readonly_guard` proves a template with a write verb is rejected; a query runs with bytes cap set and
  with the principal's region filter applied.

### Stage 6 — Guardrails (input + output), wired into the path
- `guardrails.py`: `scan_input(question)` (flag injection/secret patterns) and `redact_output(payload)` (strip any
  leaked SQL/schema/PII from the user-facing answer). Stubs are fine but must be on the request path, not dead code.
- Test: an input with an obvious injection marker is flagged; an output containing a table name is redacted.

### Stage 7 — Orchestrator: wire the full loop
- `orchestrator.py`: the bounded loop tying it together:
  1. audit-open + scan_input
  2. router.classify → intent
  3. grounding_service: MATCH / AMBIGUOUS / OUT_OF_SET
     - AMBIGUOUS → return `needs_clarification` (specific question)
     - OUT_OF_SET → return `declined` (routed to human)
  4. policy.authorize → deny short-circuits to declined+audit
  5. warehouse.query (read-only, as principal, bytes-capped)
  6. redact_output → build AnswerPayload (answer + provenance + confidence)
  7. audit-close (full record) → return ApiResponse
  - Enforce a hard step cap and a token/cost budget; abort → error path (audited).
- Replace Stage 1's hardcoded return with the real loop.
- Tests: happy path returns an answer WITH provenance; clarification path and decline path both return correctly and
  are audited; the read-only guard holds end-to-end.

### Stage 8 — README + run instructions + TODO(harden) sweep
- README: what it is, the non-negotiables, how to run locally, the env vars, and a "Before hardening" section listing
  every `# TODO(harden)` and `# DECISION-NEEDED` seam (identity→real RLS, semantic layer→real dbt/Cube, model
  routing policy, real MCP transport, guardrail rules, artifacts server).
- Print the skeleton's known limitations explicitly so no one mistakes it for production.

## Acceptance for the whole session
- `POST /ask "What was total revenue last month?"` with a valid principal → `ApiResponse status=ok` with answer,
  source (metric id), resolved_interpretation, confidence — and a full audit record.
- An ambiguous question → `needs_clarification`. An out-of-scope question → `declined`. Both audited.
- A template with a write verb → rejected. Every BigQuery job has a bytes cap. The loop is step-capped.
- Every request has exactly one reconstructable audit record. No secrets in code. No raw-string SQL.
- All tests green.

Build Stage 1 now. Then stop and show me the diff.
