# -*- coding: utf-8 -*-
"""Rerank search results using Hugging Face cross-encoder (ms-marco-MiniLM-L-6-v2)."""

from __future__ import annotations

from typing import Any, List, Tuple

from src.config import get_settings

# Lazy-loaded so ingest (no search) runs without sentence_transformers installed.
_RERANKER: Any = None


def get_reranker() -> Any:
    global _RERANKER
    if _RERANKER is None:
        from sentence_transformers import CrossEncoder
        model_name = get_settings().reranker_model
        _RERANKER = CrossEncoder(model_name)
    return _RERANKER


def rerank(
    query: str,
    documents: List[str],
    top_k: int,
) -> List[Tuple[int, float]]:
    """
    Rerank documents by relevance to query. Returns list of (original_index, score).
    """
    if not documents:
        return []
    model = get_reranker()
    pairs = [[query, d] for d in documents]
    scores = model.predict(pairs)
    indexed = list(enumerate(scores))
    indexed.sort(key=lambda x: x[1], reverse=True)
    return indexed[:top_k]
