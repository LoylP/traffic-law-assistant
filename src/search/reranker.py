# -*- coding: utf-8 -*-
"""Rerank search results: OpenSearch ML _predict API or local cross-encoder (ms-marco-MiniLM-L-6-v2)."""

from __future__ import annotations

import logging
import os
from typing import Any, List, Tuple

from src.config import get_settings

# Lazy-loaded so ingest (no search) runs without sentence_transformers installed.
_RERANKER: Any = None


def rerank_via_opensearch_ml(
    query: str,
    documents: List[str],
    top_k: int,
    model_id: str,
    client: Any,
) -> List[Tuple[int, float]]:
    """
    Rerank using OpenSearch ML /_plugins/_ml/models/{id}/_predict/ (same as Go RerankReq.SendRequest).
    Returns list of (original_index, score) for top_k, sorted by score descending.
    """
    if not documents or not model_id:
        return []
    from src.search.opensearch_client import ml_rerank_predict
    scores = ml_rerank_predict(model_id, query, documents, client=client)
    if len(scores) != len(documents):
        scores = (scores + [0.0] * len(documents))[:len(documents)]
    indexed = list(enumerate(scores))
    indexed.sort(key=lambda x: x[1], reverse=True)
    return indexed[:top_k]


def get_reranker() -> Any:
    global _RERANKER
    if _RERANKER is None:
        # Suppress verbose load report and progress bar on first load
        for name in ("transformers", "sentence_transformers", "safetensors"):
            logging.getLogger(name).setLevel(logging.WARNING)
        prev_verbosity = os.environ.get("TRANSFORMERS_VERBOSITY")
        prev_hub_progress = os.environ.get("HF_HUB_DISABLE_PROGRESS_BARS")
        os.environ["TRANSFORMERS_VERBOSITY"] = "error"
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        try:
            from sentence_transformers import CrossEncoder
            settings = get_settings()
            model_name = settings.reranker_model
            token = (settings.hf_token or "").strip() or None
            _RERANKER = CrossEncoder(model_name, token=token)
        finally:
            if prev_verbosity is None:
                os.environ.pop("TRANSFORMERS_VERBOSITY", None)
            else:
                os.environ["TRANSFORMERS_VERBOSITY"] = prev_verbosity
            if prev_hub_progress is None:
                os.environ.pop("HF_HUB_DISABLE_PROGRESS_BARS", None)
            else:
                os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = prev_hub_progress
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
