# SPEC.md — Architecture Spec-as-Prompt (Data-Answers Agent, IF-RES-2026-061)

> Reference spec for Cursor and the team. `.cursorrules` governs behaviour; `BUILD-PROMPT.md` drives the first
> session (the walking skeleton). This document is the full architecture the skeleton grows into, plus the phased
> roadmap and the decisions that were defaulted for the skeleton and must be revisited before hardening.

---

## 1. Problem (why the design is shaped this way)
Business users needing data currently file a Jira ticket; a scarce data engineer answers it after 2–3 days of
back-and-forth, most of it CLARIFYING the question. We are replacing that queue for a bounded set of repetitive,
well-understood questions. The user is NON-TECHNICAL and cannot verify SQL. Therefore:
- A confidently-wrong answer is worse than no answer → precision over recall; refuse/clarify over guess.
- Trust is the product → every answer ships with provenance, resolved interpretation, and confidence.
- The bottleneck is clarification + knowledge-location + queue, NOT SQL generation. SQL is the easy part.

## 2. Component architecture (target)
```
Consuming system ──(POST /ask, carries end-user principal)──▶ Agent Service (FastAPI, stateless, ApiResponse<T>)
  Agent Service:
    Orchestration Loop (bounded: plan→resolve→authorize→execute→answer; step-cap + cost-cap)
    Model Router (cheap classify tier  |  frontier reasoning tier  |  embedding retrieval)
    Guardrail Plane (input scan · tool validation · output redaction)
    Policy Plane (PEP→PDP: deterministic allow/deny on every tool call)
    Identity Broker (principal → short-lived, downscoped credential)
  ── MCP boundary (MCP client attaches per-request identity) ──
    MCP "warehouse" (read-only query tool) ─▶ BigQuery (RLS + masking = the policy engine)
    MCP "grounding" (semantic layer + verified-query library) ─▶ dbt/Cube/registry + query cache
    MCP "artifacts" (docs/dashboards/catalog RAG) ─▶ vector + object store        [DEFERRED]
  Observability/Audit spans every step (who · intent · query · identity · allow/deny · bytes · cost · latency)
```
Key property: for the core data-security guarantees, the WAREHOUSE enforces (RLS, masking, read-only role). Our code
orchestrates and gates; it is not the last line of data defense. That is what keeps "agent visibility = human
visibility" true.

## 3. The non-negotiables (full statement)
1. **Grounding** — No free-form SQL on raw schemas as the primary path. Every answer traces to a defined metric or a
   vetted query. Out-of-set → decline/route, never extrapolate.
2. **Governance, enforced at the data layer** — Not in the prompt. The agent acts AS the user. No all-seeing service
   account. Model authorization as PEP→PDP; no query reaches the warehouse without an allow decision. PII masked at
   query time by role.
3. **Read-only, defence-in-depth** — Mutation structurally impossible: read-only role + no write verbs exposed in the
   warehouse tool.
4. **API contract** — `ApiResponse<T>` on all routes. Carries answer, provenance, confidence, and clarification
   state. Identity is part of the contract (caller passes the end-user principal). Multi-turn: a call may return a
   question instead of an answer. Auth, rate-limiting, idempotency expected.
5. **Auditability** — Every request reconstructable. Non-negotiable.

## 4. Request lifecycle (target, identity-annotated)
1. Ingress — validate principal; reject if a human principal is required and only a service token is present.
2. Identity mint — Identity Broker → short-lived, downscoped credential bound to the user.
3. Guardrail (input) — injection/secret scan.
4. Plan — classify intent (cheap tier); decide grounding needed.
5. Ground/resolve (MCP grounding) — MATCH → grounded query from the verified library; AMBIGUOUS → clarify (turn
   ends); OUT_OF_SET → decline/route. Never improvise SQL.
6. Authorize (PEP→PDP) — allow/deny; deny short-circuits (audited).
7. Execute (MCP warehouse, carrying user credential) — read-only, AS the user; RLS + masking apply; bytes-scanned
   cap; identity-aware cache.
8. Guardrail (output) — redact leaked PII/schema.
9. Respond — ApiResponse with answer, resolved interpretation, source, confidence, clarification state.

## 5. Best-practice patterns we are adopting (from mature agent tooling, e.g. Cursor)
- **Plan→act→observe→repeat** core loop (ReAct-style), bounded by step and cost caps. [in skeleton]
- **Retrieval-heavy grounding** — semantic match over a metric/verified-query registry rather than dumping schema.
  Analogue of codebase embedding + agentic search. [in skeleton, simple; real embeddings later]
- **Structural/graph awareness of the semantic layer** — reason over metric lineage and join paths the way a code
  agent reasons over an AST. This is our join-path-resolution mechanism. [POST-SKELETON — see roadmap]
- **Multi-model routing** — cheap/fast model for classification+intent, frontier model for reasoning, embedding
  model for retrieval. Directly serves the cost story. [seam in skeleton; policy tuned later]
- **Bounded tool surface** — a small, typed, read-only toolset (query_warehouse, retrieve_grounding), MCP-shaped so
  real MCP servers slot in. [in skeleton as typed functions]
- **Delta re-indexing** — when the registry/semantic layer changes, re-embed only the deltas. [POST-SKELETON]
- **Human-in-the-loop as the control surface** — inverted vs a coding agent: we don't gate mutations (we're
  read-only); we gate on uncertainty (clarify) and scope (decline/route to human). [in skeleton]
- NOT adopted, deliberately: the "apply model" / diff-merge pattern (we mutate nothing); mutation checkpointing
  (nothing to roll back).

## 6. Cost & latency architecture
- Loop: hard step cap + token/cost budget; abort over budget.
- Warehouse: `maximum_bytes_billed` on every job (non-negotiable).
- Cache: identity-aware (same query, different user → different RLS results; cache MUST key on identity or it leaks);
  TTL by query class (freshness: "last month" tolerates staleness, "today so far" does not); pre-warm the known
  repetitive wedge.
- Model routing (see §5) is a primary cost lever: cheap decisions on the cheap tier.
- Verified-query hits skip synthesis entirely; cache hits skip the full loop.

## 7. Defaulted decisions for the skeleton (REVISIT before hardening)
| Decision | Skeleton default | Revisit when |
|---|---|---|
| Identity pattern | Pattern A **stub**: principal threaded + WHERE-clause row-filter stand-in; single dev cred | Before any real data / multi-user. Replace with BigQuery RLS via WIF/impersonation. **Feasibility-critical — validate first.** |
| Semantic-layer substrate | Flat `registry.yaml` (metrics + verified-query templates) | When question variety outgrows a flat file → dbt Semantic Layer or Cube |
| Model routing policy | Two-tier seam (cheap classify / frontier reason) with simple policy | Tune routing + add embedding tier once we have real query volume + cost data |
| MCP transport | Typed tool functions standing in for MCP servers | When we split services or expose outbound MCP |
| Artifacts/RAG server | Out of scope | When unstructured retrieval enters scope (may stay deferred) |
| Guardrail depth | Input/output stubs on the path | Before production: real injection detection + PII/schema redaction |

These are SKELETON conveniences, not architecture decisions. Do not treat a default here as settled. Each has a
`# TODO(harden)` / `# DECISION-NEEDED` seam in code.

## 8. Roadmap (phases beyond the skeleton)
- **Phase 0 — Walking skeleton** (BUILD-PROMPT.md): one grounded question, one user, all layers thin-but-real,
  every path audited. Done = acceptance in BUILD-PROMPT.md.
- **Phase 1 — Real grounding + real identity**: back the registry with a real semantic layer; replace the identity
  stub with true per-user BigQuery auth (RLS/masking enforced by the warehouse). Add structural/graph reasoning over
  the semantic layer (join-path resolution). Expand the verified-query library for one high-volume domain.
- **Phase 2 — Real MCP + cost hardening**: split warehouse/grounding into real MCP servers with per-request identity;
  add the embedding retrieval tier; implement identity-aware caching + TTL-by-class + pre-warming; tune model
  routing on real cost data; harden guardrails.
- **Phase 3 — Evaluation + trust**: eval harness measuring deflection rate, time-to-answer, refusal-vs-hallucination,
  clarification rate. Instrument the metrics the loop was built to expose.
- **Phase 4 — Productization (MicroSaaS)**: multi-tenancy + tenant isolation; consider OUTBOUND MCP (our agent as a
  tool other agents call) as a differentiator; broaden domains via curated onboarding.

## 9. Success metrics the system must let us measure (build the hooks now)
- Deflection rate (% answered with no human), time-to-answer (vs 2–3 day baseline), refusal-vs-hallucination (want
  high refusal, near-zero confident-wrong), clarification rate (a tuning dial). The skeleton's audit records should
  already capture enough to compute these later.

## 10. Explicitly out of scope (all phases until stated otherwise)
Arbitrary novel questions / open-ended exploration; multi-source join reasoning across the raw landscape; write
operations/forecasting; a chat UI (API only); dialect portability (BigQuery only); self-serve domain onboarding;
the full 50-layer guardrail catalog; multi-agent decomposition; JIT millisecond credential grant/revoke.
