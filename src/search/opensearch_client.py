# -*- coding: utf-8 -*-
"""OpenSearch client: index creation, document insert, k-NN search."""

from __future__ import annotations

from urllib.parse import urlparse

from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError

from src.config import get_settings


def _normalize_l2(vec: list[float]) -> list[float]:
    """L2-normalize so that l2 space_type in OpenSearch matches cosine similarity."""
    import math
    n = math.sqrt(sum(x * x for x in vec))
    if n <= 0:
        return vec
    return [x / n for x in vec]


# text-embedding-3-small default dimension
EMBEDDING_DIMENSION = 1536

# faiss engine does not support cosinesimil; use l2 with normalized vectors for cosine-like behavior
INDEX_BODY = {
    "settings": {"index.knn": True},
    "mappings": {
        "properties": {
            "embedding": {
                "type": "knn_vector",
                "dimension": EMBEDDING_DIMENSION,
                "method": {"name": "hnsw", "space_type": "l2"},
            },
            "description_natural": {"type": "text"},
            "normalized_violation": {"type": "text"},
            "vehicle_type": {"type": "keyword"},
            "context_condition": {"type": "text"},
            "fine_min": {"type": "integer"},
            "fine_max": {"type": "integer"},
            "additional_sanctions": {"type": "text"},
            "legal_basis": {"type": "text"},
            "confidence_label": {"type": "keyword"},
            "violation_id": {"type": "keyword"},
        }
    },
}


def _parse_url(url: str) -> dict:
    p = urlparse(url)
    host = p.hostname or "localhost"
    port = p.port or 9200
    use_ssl = p.scheme == "https"
    return {"host": host, "port": port, "use_ssl": use_ssl}


def get_opensearch_client() -> OpenSearch:
    s = get_settings()
    parsed = _parse_url(s.opensearch_url)
    kwargs = {
        "hosts": [{"host": parsed["host"], "port": parsed["port"]}],
        "use_ssl": parsed["use_ssl"],
        "verify_certs": s.opensearch_ssl_verify,
    }
    if s.opensearch_username and s.opensearch_password:
        kwargs["http_auth"] = (s.opensearch_username, s.opensearch_password)
    return OpenSearch(**kwargs)


def ensure_index(client: OpenSearch | None = None, index_name: str | None = None) -> str:
    """Create traffic_law_index if it does not exist. Returns index name."""
    client = client or get_opensearch_client()
    name = index_name or get_settings().traffic_law_index
    if not client.indices.exists(index=name):
        client.indices.create(index=name, body=INDEX_BODY)
    return name


def index_document(
    doc: dict,
    embedding: list[float],
    doc_id: str | None = None,
    client: OpenSearch | None = None,
    index_name: str | None = None,
) -> str:
    """
    Insert one document with embedding into OpenSearch.
    doc must contain: description_natural, normalized_violation, vehicle_type, etc.
    Returns the OpenSearch document id.
    """
    client = client or get_opensearch_client()
    name = index_name or get_settings().traffic_law_index
    ensure_index(client=client, index_name=name)
    body = {**doc, "embedding": _normalize_l2(embedding)}
    r = client.index(index=name, id=doc_id, body=body, refresh=True)
    return r["_id"]


def knn_search(
    query_vector: list[float],
    k: int = 20,
    query_text: str | None = None,
    search_pipeline: str | None = None,
    client: OpenSearch | None = None,
    index_name: str | None = None,
) -> list[dict]:
    """
    k-NN search by vector. Returns list of hits with _source and _score.
    If search_pipeline is set and query_text is provided, uses OpenSearch rerank pipeline
    (no manual rerank). Otherwise returns top k by vector similarity.
    """
    client = client or get_opensearch_client()
    name = index_name or get_settings().traffic_law_index
    body = {
        "size": k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": _normalize_l2(query_vector),
                    "k": k,
                }
            }
        },
    }
    if query_text and search_pipeline:
        body["ext"] = {
            "rerank": {
                "query_context": {"query_text": query_text},
            }
        }
    try:
        if search_pipeline:
            resp = client.search(index=name, body=body, params={"search_pipeline": search_pipeline})
        else:
            resp = client.search(index=name, body=body)
    except NotFoundError:
        return []
    return [hit for hit in resp.get("hits", {}).get("hits", [])]
