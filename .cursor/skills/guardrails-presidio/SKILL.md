---
name: guardrails-presidio
description: >-
  Input/output guardrails with Presidio and injection detection for the
  Data-Answers Agent. Use when hardening guardrails.py beyond skeleton stubs,
  detecting PII, secrets, or schema leaks in responses.
---

# Guardrails — Presidio & Injection Detection (Hardening)

## Skeleton (Phase 0)

Regex stubs on the request path — must be wired, not dead code:

```python
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s*:",
    r"```sql",
]
SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",           # AWS key
    r"-----BEGIN (RSA |)PRIVATE KEY-----",
]
```

## Phase 2: Microsoft Presidio (OSS)

```toml
"presidio-analyzer>=2.2",
"presidio-anonymizer>=2.2",
```

```python
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine

analyzer = AnalyzerEngine()

def redact_pii(text: str) -> str:
    results = analyzer.analyze(text=text, language="en")
    return AnonymizerEngine().anonymize(text, results).text
```

## Output redaction targets

Strip from user-facing `AnswerPayload.answer`:

- SQL keywords + table/dataset patterns (`FROM \`project.dataset.table\``)
- Column names from registry leak
- PII entities (email, phone, SSN, credit card)
- Internal error stack traces

```python
SCHEMA_LEAK = re.compile(r"`[\w-]+\.[\w-]+\.[\w-]+`|[a-z_]+\.[a-z_]+\.[a-z_]+", re.I)
```

## Input scan actions

| Severity | Action |
|----------|--------|
| Injection detected | `declined` or `error` — audited, do not proceed to warehouse |
| Secret in question | Redact from audit log; warn user |
| Benign | Continue to grounding |

## Rules

- Guardrails run **before** grounding (input) and **after** warehouse (output)
- Redaction changes user payload only — full detail stays in audit (with PII masked in audit too for production)
- Never use prompt instructions as security — structural enforcement only

```python
# TODO(harden): expand rule catalog; wire Presidio; add rebuff/Lakera if needed
```
