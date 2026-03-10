# -*- coding: utf-8 -*-
"""Search: embed query -> k-NN -> rerank (pipeline / OpenSearch ML / local cross-encoder) -> top_k."""

from __future__ import annotations

import threading
from typing import List

from src.config import get_settings
from src.search.embeddings import get_embeddings
from src.search.ingest import _get_llm
from src.search.opensearch_client import (
    ensure_search_pipeline,
    get_opensearch_client,
    get_or_register_rerank_model_id,
    knn_search,
)
from src.search.reranker import rerank, rerank_via_opensearch_ml

# Cached OpenSearch ML rerank model ID (loaded automatically like Go ensureRerankingInitialized)
_ml_rerank_model_id: str | None = None
_ml_rerank_lock = threading.Lock()


def _get_ml_rerank_model_id() -> str | None:
    """Return OPENSEARCH_RERANK_MODEL_ID if set, else auto-load via getLLMModel-style get/register/deploy."""
    s = get_settings()
    explicit_id = (s.opensearch_rerank_model_id or "").strip()
    if explicit_id:
        return explicit_id
    global _ml_rerank_model_id
    with _ml_rerank_lock:
        if _ml_rerank_model_id:
            return _ml_rerank_model_id
        try:
            client = get_opensearch_client()
            _ml_rerank_model_id = get_or_register_rerank_model_id(client=client)
            return _ml_rerank_model_id
        except Exception:
            return None

def generate_search_query(user_query: str) -> str:
    """
    Use LLM to turn the user's question into a search query with correct legal/traffic-violation wording,
    common phrases, and synonyms so vector search matches the indexed violation descriptions.
    """
    user_query = (user_query or "").strip()
    if not user_query:
        return user_query
    try:
        llm = _get_llm()
        messages = [
            (
                "system",
                """You are an expert in traffic and legal violations. Given a user question, output a single, concise search query that uses the correct legal terms, common phrases, and synonyms people use for traffic violations (e.g. vượt đèn đỏ, chạy quá tốc độ, không đội mũ bảo hiểm, đỗ xe sai quy định). Output only the search query, no explanation.

# Rule:
- Do not push the time range into the search query.
- Use the words are used on the Law Corpus.
""",
            ),
            ("human", user_query),
        ]
        response = llm.invoke(messages)
        out = (response.content or "").strip()
        return out if out else user_query
    except Exception:
        return user_query

def search(query: str) -> List[dict]:
    """
    Search by text: embed query, k-NN search, then rerank.
    - If SEARCH_PIPELINE is set: OpenSearch search pipeline does rerank (no extra step).
    - Elif OpenSearch ML rerank available: use _predict (model ID from config or auto-loaded like Go getLLMModel).
    - Else: in-app cross-encoder rerank. Rerank uses vector_embedding_text when present.
    """
    s = get_settings()
    top_k = s.top_k
    pipeline_name = (s.search_pipeline or "").strip()
    window_size = s.search_window_size

    search_query = query  # or generate_search_query(query)
    embeddings = get_embeddings()
    query_vector = embeddings.embed_query(search_query)

    # If SEARCH_PIPELINE is set, ensure the pipeline exists (uses current rerank model) then use it
    use_pipeline = False
    if pipeline_name:
        ml_model_id = _get_ml_rerank_model_id()
        if ml_model_id:
            try:
                client = get_opensearch_client()
                ensure_search_pipeline(pipeline_name, ml_model_id, client=client)
                use_pipeline = True
            except Exception:
                pass  # fall back to no pipeline + manual rerank

    hits = knn_search(
        query_vector,
        k=window_size,
        query_text=search_query if use_pipeline else None,
        search_pipeline=pipeline_name if use_pipeline else None,
    )
    if not hits:
        return []

    def _doc_for_response(hit: dict, score: float) -> dict:
        doc = dict(hit["_source"])
        doc.pop("embedding", None)  # exclude vector from API/UI
        doc["score"] = float(score)
        doc["_id"] = hit.get("_id")
        return doc

    if use_pipeline:
        # OpenSearch already reranked; take top_k and use returned score
        results = [_doc_for_response(hit, hit.get("_score", 0)) for hit in hits[:top_k]]
        return results

    # Rerank with vector_embedding_text (contexted text used for embedding), fallback description_natural
    texts = [
        (h["_source"].get("vector_embedding_text") or h["_source"].get("description_natural") or "")
        for h in hits
    ]

    ml_rerank_id = _get_ml_rerank_model_id()
    if ml_rerank_id:
        client = get_opensearch_client()
        reranked = rerank_via_opensearch_ml(search_query, texts, top_k=top_k, model_id=ml_rerank_id, client=client)
    else:
        reranked = rerank(search_query, texts, top_k=top_k)

    results = [_doc_for_response(hits[idx], score) for idx, score in reranked]
    return results


class SearchService:
    """Convenience wrapper around search()."""

    def search(self, query: str) -> List[dict]:
        return search(query)
