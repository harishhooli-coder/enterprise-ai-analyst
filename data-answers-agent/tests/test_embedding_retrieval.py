"""Tests for embedding-based metric retrieval (Phase 1)."""

from app.grounding.grounding_service import GroundingService
from app.grounding.retrieval import EmbeddingRetriever, HashEmbedder, KeywordRetriever


def test_embedding_matches_paraphrase_with_registry_alias():
    registry = [
        {
            "id": "total_revenue",
            "name": "Total Revenue",
            "description": "Sum of gross revenue for a calendar month by region",
            "aliases": ["total revenue", "gross revenue", "how much did we sell"],
            "template": "SELECT 1",
            "parameters": [],
        },
        {
            "id": "active_customers",
            "name": "Active Customers",
            "description": "Count of distinct active customers in a calendar month",
            "aliases": ["active customers"],
            "template": "SELECT 2",
            "parameters": [],
        },
    ]
    retriever = EmbeddingRetriever(embedder=HashEmbedder())
    service = GroundingService(retriever=retriever, registry=registry)

    result = service.resolve("How much did we sell last month?")

    assert result.status == "match"
    assert result.metric_id == "total_revenue"


def test_keyword_does_not_match_paraphrase_without_alias():
    registry = [
        {
            "id": "total_revenue",
            "name": "Total Revenue",
            "description": "Sum of gross revenue for a calendar month by region",
            "aliases": ["total revenue", "gross revenue"],
            "template": "SELECT 1",
            "parameters": [],
        },
    ]
    service = GroundingService(retriever=KeywordRetriever(), registry=registry)

    result = service.resolve("How much did we sell last month?")

    assert result.status == "out_of_set"


def test_embedding_ambiguity_when_scores_are_close():
    registry = [
        {
            "id": "total_revenue",
            "name": "Total Revenue",
            "description": "Gross revenue for a calendar month",
            "aliases": ["revenue", "total revenue"],
            "template": "SELECT 1",
            "parameters": [],
            "ambiguity_group": "revenue",
        },
        {
            "id": "net_revenue",
            "name": "Net Revenue",
            "description": "Revenue after returns for a calendar month",
            "aliases": ["revenue", "net revenue"],
            "template": "SELECT 2",
            "parameters": [],
            "ambiguity_group": "revenue",
        },
    ]
    service = GroundingService(retriever=KeywordRetriever(), registry=registry)

    result = service.resolve("What was revenue last month?")

    assert result.status == "ambiguous"
    assert set(result.candidates or []) == {"total_revenue", "net_revenue"}


def test_order_count_metric_resolves():
    from app.grounding.grounding_service import grounding_service

    result = grounding_service.resolve("How many orders did we have last month?")

    assert result.status == "match"
    assert result.metric_id == "order_count"
