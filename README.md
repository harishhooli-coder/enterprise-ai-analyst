# Cursor Handover Package — Data-Answers Agent (IF-RES-2026-061)

Three files, one job: hand the v1 build to Cursor without losing the architecture we designed.

## What each file is, and how to use it

**`.cursorrules`** — the persistent guardrails. Drop this in your repo root. Cursor keeps it in context on every
action. It encodes the five non-negotiables (grounding, governance, identity, read-only, auditable), the coding
rules (no secrets, no string-concatenated SQL, always bytes-cap, always audit), and the skeleton defaults for the
open decisions so Cursor doesn't stall or improvise architecture. This is the file that stops Cursor from "helpfully"
free-forming SQL or building a service account that sees everything.

**`BUILD-PROMPT.md`** — the kickoff. Paste it into Cursor Composer (Agent mode) to scaffold the walking skeleton in 8
staged steps. It's deliberately stop-and-show after each stage so you review diffs and stay in control. Scope is
fenced hard: one grounded question, one user, all layers thin-but-real, every path audited.

**`SPEC.md`** — the reference. The full target architecture, the best-practice patterns we're adopting (and the ones
we deliberately aren't), the defaulted decisions with when-to-revisit, and the phased roadmap the skeleton grows
into. Point Cursor (and the team) here for "why is it shaped this way."

## Suggested flow
1. Create the repo, add `.cursorrules` to the root.
2. Read `SPEC.md` §7 first — the defaulted decisions. Confirm you're OK with each skeleton default (especially the
   identity stub) before building.
3. Open Composer, paste `BUILD-PROMPT.md`, build Stage 1, review the diff, continue stage by stage.
4. After Phase 0 (skeleton) is green, the `# TODO(harden)` sweep in the README (Stage 8) is your Phase 1 backlog.

## The one thing to resolve before hardening
The identity pattern is stubbed for the skeleton (principal threaded + WHERE-clause row-filter stand-in). Before any
real data or real users, validate that per-user identity into BigQuery is feasible in your GCP setup (Workload
Identity Federation / impersonation, connection cost). This is the feasibility-critical decision from the
architecture doc — everything in the security model depends on it. Do not ship past the skeleton without it.

## Provenance
This package operationalizes IF-RES-2026-061 (the PM architecture brief) and its companion technical architecture
(the MCP-centered design + end-to-end flow diagram). If you need the "why," those documents are the source.
