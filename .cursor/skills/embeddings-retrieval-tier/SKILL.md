---
name: embeddings-retrieval-tier
description: >-
  Embedding-based retrieval for metric registry matching in the Data-Answers
  Agent. Use when adding sentence-transformers, cosine similarity, vector
  indexing, or the embedding tier to model_router / grounding_service.
---

# Embeddings Retrieval Tier (Phase 1–2)

## Purpose

Replace keyword matching with semantic retrieval over metric descriptions and aliases. Third tier alongside cheap classify and frontier reason.

## Skeleton stack (in-memory, no vector DB)

```toml
# optional deps for Phase 1+
"sentence-transformers>=3.0",
"numpy>=1.26",
"scikit-learn>=1.5",
```

## Index at startup

```python
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")  # small, fast, OSS

def build_index(metrics: list[MetricDef]) -> tuple[np.ndarray, list[str]]:
    texts = [f"{m.name}. {m.description}. {' '.join(m.aliases)}" for m in metrics]
    embeddings = model.encode(texts, normalize_embeddings=True)
    ids = [m.id for m in metrics]
    return embeddings, ids
```

## Query

```python
def retrieve(question: str, embeddings, ids, top_k=3, threshold=0.55):
    q = model.encode([question], normalize_embeddings=True)
    scores = (embeddings @ q.T).flatten()
    ranked = sorted(zip(ids, scores), key=lambda x: -x[1])[:top_k]
    if ranked[0][1] < threshold:
        return GroundingResult(status="out_of_set")
    if len(ranked) > 1 and ranked[1][1] > threshold and ranked[0][1] - ranked[1][1] < 0.05:
        return GroundingResult(status="ambiguous", candidates=[r[0] for r in ranked[:2]])
    return GroundingResult(status="match", metric_id=ranked[0][0])
```

## Delta re-indexing (Phase 2)

When registry changes, re-embed only changed metric ids — not full rebuild.

```python
# TODO(harden): delta re-index on registry webhook / CI deploy
```

## Cost note

Embedding calls are cheaper than frontier reasoning. Route retrieval here; reserve Claude for answer formatting when needed.

## Phase 2 vector DB (artifacts/RAG — deferred)

For unstructured docs: Qdrant, pgvector, or Weaviate. **Not** needed for metric registry in Phase 1.
