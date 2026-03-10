# -*- coding: utf-8 -*-
"""Search: embed query -> k-NN -> (OpenSearch rerank pipeline or in-app rerank) -> top_k."""

from __future__ import annotations

from typing import List

from src.config import get_settings
from src.search.embeddings import get_embeddings
from src.search.opensearch_client import knn_search
from src.search.reranker import rerank


def search(query: str) -> List[dict]:
    """
    Search by text: embed query, k-NN search. If SEARCH_PIPELINE is set, use OpenSearch
    native rerank; otherwise rerank in-app with cross-encoder. Returns top_k with score.
    """
    s = get_settings()
    top_k = s.top_k
    use_pipeline = (s.search_pipeline or "").strip()
    candidate_k = max(top_k * 4, 20) if not use_pipeline else max(top_k * 3, 20)

    embeddings = get_embeddings()
    query_vector = embeddings.embed_query(query)
    hits = knn_search(
        query_vector,
        k=candidate_k,
        query_text=query if use_pipeline else None,
        search_pipeline=s.search_pipeline if use_pipeline else None,
    )
    if not hits:
        return []

    if use_pipeline:
        # OpenSearch already reranked; take top_k and use returned score
        results = []
        for hit in hits[:top_k]:
            doc = dict(hit["_source"])
            doc["score"] = float(hit.get("_score", 0))
            doc["_id"] = hit.get("_id")
            results.append(doc)
        return results

    # In-app rerank
    texts = [h["_source"].get("description_natural", "") or "" for h in hits]
    reranked = rerank(query, texts, top_k=top_k)
    results = []
    for idx, score in reranked:
        hit = hits[idx]
        doc = dict(hit["_source"])
        doc["score"] = float(score)
        doc["_id"] = hit.get("_id")
        results.append(doc)
    return results


class SearchService:
    """Convenience wrapper around search()."""

    def search(self, query: str) -> List[dict]:
        return search(query)
