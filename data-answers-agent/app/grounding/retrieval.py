"""Metric retrieval strategies: keyword, hash-embedding, and optional sentence-transformers."""

from __future__ import annotations

import hashlib
import math
import re
from abc import ABC, abstractmethod
from typing import Any, Protocol

# TODO(harden): delta re-index on registry webhook / CI deploy


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _metric_text(metric: dict[str, Any]) -> str:
    parts = [
        metric.get("name", ""),
        metric.get("id", "").replace("_", " "),
        metric.get("description", ""),
        " ".join(metric.get("aliases", [])),
    ]
    return _normalize(" ".join(part for part in parts if part))


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _hash_embed(text: str, *, dim: int = 128) -> list[float]:
    """Deterministic bag-of-words hash embedding — no external model required."""
    vec = [0.0] * dim
    for token in _normalize(text).split():
        digest = hashlib.sha256(token.encode()).hexdigest()
        for i in range(3):
            idx = int(digest[i * 8 : i * 8 + 8], 16) % dim
            vec[idx] += 1.0
    return vec


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashEmbedder:
    """Lightweight embedder for CI and environments without ML deps."""

    def __init__(self, dim: int = 128) -> None:
        self._dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_hash_embed(text, dim=self._dim) for text in texts]


class SentenceTransformerEmbedder:
    """Optional semantic embedder when sentence-transformers is installed."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [vector.tolist() for vector in vectors]


def build_embedder(prefer_transformer: bool = True) -> Embedder:
    if prefer_transformer:
        try:
            return SentenceTransformerEmbedder()
        except ImportError:
            pass
    return HashEmbedder()


class RetrievalRank:
    def __init__(self, metric_id: str, score: float) -> None:
        self.metric_id = metric_id
        self.score = score


class MetricRetriever(ABC):
    @abstractmethod
    def rank(self, question: str, registry: list[dict[str, Any]]) -> list[RetrievalRank]:
        pass


class KeywordRetriever(MetricRetriever):
    """Phase 0 keyword/alias matcher."""

    def rank(self, question: str, registry: list[dict[str, Any]]) -> list[RetrievalRank]:
        normalized = _normalize(question)
        ranked: list[RetrievalRank] = []
        for metric in registry:
            best = 0
            for term in self._match_terms(metric):
                if term in normalized:
                    best = max(best, len(term))
            if best > 0:
                ranked.append(RetrievalRank(metric["id"], float(best) / 100.0))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked

    @staticmethod
    def _match_terms(metric: dict[str, Any]) -> list[str]:
        terms = [metric.get("name", ""), metric.get("id", "").replace("_", " ")]
        terms.extend(metric.get("aliases", []))
        return [_normalize(term) for term in terms if term.strip()]


class EmbeddingRetriever(MetricRetriever):
    """Cosine similarity over metric name, description, and aliases."""

    def __init__(
        self,
        embedder: Embedder | None = None,
        *,
        prefer_transformer: bool = True,
    ) -> None:
        self._embedder = embedder or build_embedder(prefer_transformer=prefer_transformer)
        self._index: dict[str, list[float]] = {}
        self._registry_ids: list[str] = []

    def build_index(self, registry: list[dict[str, Any]]) -> None:
        texts = [_metric_text(metric) for metric in registry]
        vectors = self._embedder.embed(texts)
        self._index = {metric["id"]: vector for metric, vector in zip(registry, vectors)}
        self._registry_ids = [metric["id"] for metric in registry]

    def rank(self, question: str, registry: list[dict[str, Any]]) -> list[RetrievalRank]:
        if not self._index or len(self._index) != len(registry):
            self.build_index(registry)

        query_vector = self._embedder.embed([question])[0]
        ranked = [
            RetrievalRank(metric_id, _cosine(query_vector, self._index[metric_id]))
            for metric_id in self._registry_ids
        ]
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked


def select_retriever(mode: str, *, prefer_transformer: bool = True) -> MetricRetriever:
    if mode == "keyword":
        return KeywordRetriever()
    if mode == "embedding":
        return EmbeddingRetriever(prefer_transformer=prefer_transformer)
    # auto: embedding with hash fallback when transformers unavailable
    return EmbeddingRetriever(prefer_transformer=prefer_transformer)
