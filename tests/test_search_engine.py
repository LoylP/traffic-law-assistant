# -*- coding: utf-8 -*-
"""Tests for search engine: config, embeddings, reranker, search (optional OpenSearch)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Project root
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))


def test_config_loads_from_env() -> None:
    from src.config import get_settings

    s = get_settings()
    assert s.embedding_model
    assert s.traffic_law_index == "traffic_law_index" or os.environ.get("TRAFFIC_LAW_INDEX")
    assert s.top_k >= 1


def test_reranker_returns_top_k() -> None:
    from src.search.reranker import rerank

    query = "vượt đèn đỏ"
    docs = [
        "Vượt đèn đỏ khi tham gia giao thông",
        "Không đội mũ bảo hiểm",
        "Chạy quá tốc độ",
    ]
    out = rerank(query, docs, top_k=2)
    assert len(out) == 2
    assert all(isinstance(x, tuple) and len(x) == 2 for x in out)
    # First doc should rank higher for this query
    idx0 = out[0][0]
    assert idx0 == 0


def test_search_with_mocked_opensearch() -> None:
    """Test search flow with mocked OpenSearch (no real server)."""
    from src.search import SearchService
    from src.search.embeddings import get_embeddings
    from src.search.opensearch_client import knn_search

    # Mock k-NN to return fake hits so we only test rerank + wiring
    fake_hits = [
        {
            "_id": "V001",
            "_source": {
                "description_natural": "Vượt đèn đỏ khi tham gia giao thông",
                "violation_id": "V001",
                "legal_basis": "NĐ 168",
            },
        },
        {
            "_id": "V002",
            "_source": {
                "description_natural": "Không đội mũ bảo hiểm",
                "violation_id": "V002",
                "legal_basis": "NĐ 168",
            },
        },
    ]
    with patch("src.search.search_service.knn_search", return_value=fake_hits):
        with patch("src.search.search_service.get_embeddings") as m_emb:
            m_emb.return_value.embed_query = MagicMock(return_value=[0.1] * 1536)
            svc = SearchService()
            results = svc.search("vượt đèn đỏ")
    assert len(results) >= 1
    assert "score" in results[0]
    assert "description_natural" in results[0]
