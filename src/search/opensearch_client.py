# -*- coding: utf-8 -*-
"""OpenSearch client: index creation, document insert, k-NN search, ML rerank model get/register/deploy."""

from __future__ import annotations

import time
from urllib.parse import urlparse

from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError

from src.config import get_settings

# Default rerank model name for OpenSearch ML (same as Go getLLMModel)
DEFAULT_OPENSEARCH_RERANK_MODEL_NAME = "huggingface/cross-encoders/ms-marco-MiniLM-L-6-v2"
MODEL_REGISTRATION_TIMEOUT = 120
MODEL_DEPLOYMENT_TIMEOUT = 120


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
            # Text used to create `embedding` (contexted_text) and for reranking.
            "vector_embedding_text": {"type": "text"},
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
    timeout = max(1, s.opensearch_timeout)
    kwargs = {
        "hosts": [
            {
                "host": parsed["host"],
                "port": parsed["port"],
                "timeout": timeout,
            }
        ],
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
    # Check pipeline is exists
    print("Search pipeline: ", search_pipeline)
    try:
        if search_pipeline:
            resp = client.search(index=name, body=body, params={"search_pipeline": search_pipeline})
        else:
            resp = client.search(index=name, body=body)
    except NotFoundError:
        return []
    return [hit for hit in resp.get("hits", {}).get("hits", [])]


# Document field sent to the rerank model when using the search pipeline (must exist in index)
RERANK_PIPELINE_DOCUMENT_FIELDS = ["vector_embedding_text"]


def ensure_search_pipeline(
    pipeline_name: str,
    model_id: str,
    document_fields: list[str] | None = None,
    client: OpenSearch | None = None,
) -> None:
    """
    Create or overwrite the OpenSearch search pipeline so that k-NN search can use it
    for reranking (ext.rerank.query_context.query_text + this pipeline).
    Uses ml_opensearch rerank type with the given model_id and document_fields.
    """
    if not pipeline_name or not model_id:
        return
    client = client or get_opensearch_client()
    fields = document_fields or RERANK_PIPELINE_DOCUMENT_FIELDS
    body = {
        "response_processors": [
            {
                "rerank": {
                    "ml_opensearch": {"model_id": model_id},
                    "context": {"document_fields": fields},
                }
            }
        ]
    }
    path = f"/_search/pipeline/{pipeline_name}"
    client.transport.perform_request("PUT", path, body=body)


def ml_rerank_predict(
    model_id: str,
    query_text: str,
    text_docs: list[str],
    client: OpenSearch | None = None,
) -> list[float]:
    """
    Call OpenSearch ML rerank model /_plugins/_ml/models/{id}/_predict/.
    Request: {"query_text": "...", "text_docs": ["...", ...]}.
    Returns list of relevance scores (one per doc, same order as text_docs).
    """
    client = client or get_opensearch_client()
    path = f"/_plugins/_ml/models/{model_id}/_predict/"
    body = {"query_text": query_text, "text_docs": text_docs}
    resp = client.transport.perform_request("POST", path, body=body)
    # Response: inference_results[].output[0].data (list of float)
    scores: list[float] = []
    for item in (resp or {}).get("inference_results", []):
        outputs = (item.get("output") or [])
        if outputs:
            data = outputs[0].get("data") or []
            scores.extend(data)
        else:
            scores.append(0.0)
    return scores


def _ml_request(
    client: OpenSearch,
    method: str,
    path: str,
    body: dict | None = None,
) -> dict:
    """Perform ML plugin request; returns response body as dict. Raises on HTTP error."""
    resp = client.transport.perform_request(method, path, body=body)
    # opensearch-py may return (meta, data); we want data
    if isinstance(resp, tuple) and len(resp) == 2:
        resp = resp[1]
    return resp or {}


def _set_ml_settings(client: OpenSearch) -> None:
    """Set ML plugin cluster settings (same as Go setMLSettings)."""
    body = {
        "persistent": {
            "plugins.ml_commons.only_run_on_ml_node": "false",
            "plugins.ml_commons.model_access_control_enabled": "true",
            "plugins.ml_commons.native_memory_threshold": "99",
        }
    }
    _ml_request(client, "PUT", "/_cluster/settings", body=body)


def _search_ml_models(client: OpenSearch, model_name: str) -> list[dict]:
    """Search ML models by name (same query as Go getLLMModel). Returns hits."""
    body = {
        "query": {
            "bool": {
                "must": [
                    {"term": {"name.keyword": model_name}},
                    {"exists": {"field": "model_state"}},
                ]
            }
        }
    }
    # POST /_plugins/_ml/models/_search
    data = _ml_request(client, "POST", "/_plugins/_ml/models/_search", body=body)
    return (data.get("hits") or {}).get("hits") or []


def _register_ml_model(
    client: OpenSearch,
    name: str,
    version: str = "1.0.2",
    model_format: str = "TORCH_SCRIPT",
) -> str:
    """Register ML model; poll task until COMPLETED; return model_id."""
    body = {"name": name, "version": version, "model_format": model_format}
    data = _ml_request(client, "POST", "/_plugins/_ml/models/_register", body=body)
    task_id = (data or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"Model register response missing task_id: {data}")

    for _ in range(MODEL_REGISTRATION_TIMEOUT):
        task_data = _ml_request(client, "GET", f"/_plugins/_ml/tasks/{task_id}")
        state = (task_data or {}).get("state", "")
        model_id = (task_data or {}).get("model_id")
        if state.upper() == "COMPLETED" and model_id:
            return model_id
        if state.upper() in ("FAILED", "CANCELLED", "STOPPED"):
            raise RuntimeError(f"Model registration task failed: {state}")
        time.sleep(1)
    raise RuntimeError("Model registration task did not complete in time")


def _deploy_ml_model(client: OpenSearch, model_id: str) -> None:
    """Deploy ML model; poll task until COMPLETED (same as Go deployModel)."""
    data = _ml_request(client, "POST", f"/_plugins/_ml/models/{model_id}/_deploy")
    task_id = (data or {}).get("task_id")
    if not task_id:
        raise RuntimeError(f"Deploy response missing task_id: {data}")

    for _ in range(MODEL_DEPLOYMENT_TIMEOUT):
        task_data = _ml_request(client, "GET", f"/_plugins/_ml/tasks/{task_id}")
        state = (task_data or {}).get("state", "")
        if state.upper() == "COMPLETED":
            return
        time.sleep(1)
    raise RuntimeError("Model deployment did not complete in time")


def get_or_register_rerank_model_id(
    client: OpenSearch | None = None,
    model_name: str | None = None,
) -> str:
    """
    Get rerank model ID from OpenSearch (same as Go getLLMModel + InitializeReranking).
    Searches by model name; if not found, registers and deploys. Returns model_id.
    """
    client = client or get_opensearch_client()
    model_name = model_name or get_settings().opensearch_rerank_model_name or DEFAULT_OPENSEARCH_RERANK_MODEL_NAME

    _set_ml_settings(client)

    hits = _search_ml_models(client, model_name)
    if hits:
        model_id = hits[0].get("_id")
        source = (hits[0].get("_source") or {})
        state = (source.get("model_state") or "").upper()
        if model_id and state == "DEPLOYED":
            return model_id
        if model_id:
            _deploy_ml_model(client, model_id)
            return model_id

    model_id = _register_ml_model(client, model_name)
    _deploy_ml_model(client, model_id)
    return model_id
