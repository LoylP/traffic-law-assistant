# -*- coding: utf-8 -*-
"""
Load knowledge into the vector DB (OpenSearch + document store).

- ingest_violations_file(path): load violations JSON (description_natural, violation_id, ...)
- ingest_jsonl(path, text_field, id_field): load any JSONL; embed text_field, index full doc
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterator

from langchain_openai import ChatOpenAI

from src.config import get_settings
from src.search.document_store import ensure_document_table, save_document_id
from src.search.embeddings import get_embeddings
from src.search.opensearch_client import ensure_index, get_opensearch_client, index_document


def _get_llm() -> ChatOpenAI:
    """Build ChatOpenAI LLM from settings (for contexted text generation)."""
    s = get_settings()
    kwargs: dict = {
        "model": s.model,
        "openai_api_key": s.api_key,
        "temperature": s.temperature,
    }
    if s.base_url:
        kwargs["openai_api_base"] = s.base_url
    return ChatOpenAI(**kwargs)


def _doc_for_index(
    raw: dict,
    text_field: str,
    id_field: str,
) -> tuple[dict, str]:
    """Normalize a raw doc for our index: ensure description_natural and an id."""
    text = (raw.get(text_field) or "").strip()
    doc_id = str(raw.get(id_field) or "")
    # Index expects description_natural for search/rerank; store full doc
    doc = dict(raw)
    doc["description_natural"] = text or "(no text)"
    doc.setdefault("violation_id", doc_id or "unknown")
    return doc, doc_id or None


def ingest_violations_file(
    path: str | Path,
    *,
    index_name: str | None = None,
) -> int:
    """
    Load a violations JSON file (array of objects with description_natural, violation_id, ...)
    into OpenSearch and the document store. Returns number of documents indexed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        items = json.load(f)
    if not isinstance(items, list):
        items = [items]
    return ingest_violations(items, index_name=index_name)


def _input_hash(doc: dict) -> str:
    """Deterministic hash of the doc fields used for contexted text (for cache key)."""
    canonical = {
        "description_natural": (doc.get("description_natural") or "").strip(),
        "vehicle_type": (doc.get("vehicle_type") or "").strip(),
        "context_condition": (doc.get("context_condition") or "").strip(),
    }
    payload = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _contexted_text(doc: dict) -> str:
    """Generate search-optimized contexted text for a violation document using an LLM.

    Results are cached in a JSON file (see config contexted_text_cache) with key = input hash.

    Example output: "không chấp hành tín hiệu đèn giao thông: Vượt đèn đỏ, đèn vàng, ..."

    Args:
        doc: Document with description_natural, vehicle_type, context_condition.

    Returns:
        Contexted text for embedding/search, or a concatenation of fields on LLM failure.
    """
    fallback = " ".join(
        filter(
            None,
            [
                (doc.get("description_natural") or "").strip(),
                (doc.get("vehicle_type") or "").strip(),
                (doc.get("context_condition") or "").strip(),
            ],
        )
    ).strip() or "(no text)"

    cache_path = Path(get_settings().contexted_text_cache)
    key = _input_hash(doc)

    # Load cache: JSON object with key = input hash, value = contexted text
    cache: dict[str, str] = {}
    if cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    if key in cache and (cache[key] or "").strip():
        print(f"Cached contexted text for {key}")
        print(cache[key])
        print("--------------------------------")
        return (cache[key] or "").strip()

    try:
        llm = _get_llm()
        user_content = (
            "Generate a single contexted text for search from this violation document. "
            "Include both the formal description and natural, everyday keywords that people "
            "use when searching or talking about this (e.g. colloquial terms, common phrases). "
            "Return only the contexted text, no explanation.\n\n"
            f"description_natural: {doc.get('description_natural') or ''}\n"
            f"vehicle_type: {doc.get('vehicle_type') or ''}\n"
            f"context_condition: {doc.get('context_condition') or ''}"
        )
        messages = [
            (
                "system",
                "You generate search-optimized contexted text for traffic violation documents. "
                "Use everyday language: include natural keywords and phrases that people use in "
                "daily life when describing or searching for this violation (e.g. vượt đèn đỏ, "
                "chạy quá tốc độ, đi sai làn, không đội mũ, đỗ xe sai chỗ). Blend formal legal "
                "wording with colloquial terms so search matches how users actually ask. "
                "Output only the contexted text, nothing else.",
            ),
            ("human", user_content),
        ]
        response = llm.invoke(messages)
        text = (response.content or "").strip() + " " + (doc.get("description_natural") or "")
        text = text.strip() if text else fallback
        cache[key] = text
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        return text
    except Exception:
        return fallback


def ingest_violations(
    documents: list[dict],
    *,
    index_name: str | None = None,
) -> int:
    """
    Index a list of violation documents (each with description_natural, violation_id, etc.)
    into OpenSearch and the document store. Returns count indexed.
    """
    settings = get_settings()
    index_name = index_name or settings.traffic_law_index
    client = get_opensearch_client()
    ensure_index(client=client, index_name=index_name)
    ensure_document_table()
    embeddings = get_embeddings()
    count = 0
    for i, doc in enumerate(documents):
        
        text = _contexted_text(doc)
        vec = embeddings.embed_query(text)
        # Persist the exact text used to generate the vector embedding.
        doc["vector_embedding_text"] = text
        doc_id = doc.get("violation_id") or f"V{i+1:03d}"
        opensearch_id = index_document(
            doc=doc,
            embedding=vec,
            doc_id=doc_id,
            client=client,
            index_name=index_name,
        )
        save_document_id(opensearch_id, doc.get("violation_id", doc_id))
        count += 1
        print(f"Indexed {count}/{len(documents)} documents")
    return count


def _read_jsonl(path: Path) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def ingest_jsonl(
    path: str | Path,
    *,
    text_field: str = "text",
    id_field: str = "citation_id",
    index_name: str | None = None,
    limit: int | None = None,
) -> int:
    """
    Load a JSONL file into the vector DB. Each line is a JSON object; text_field is
    embedded, id_field used as document id. Full document is stored. Returns count indexed.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    settings = get_settings()
    index_name = index_name or settings.traffic_law_index
    client = get_opensearch_client()
    ensure_index(client=client, index_name=index_name)
    ensure_document_table()
    embeddings = get_embeddings()
    count = 0
    for i, raw in enumerate(_read_jsonl(path)):
        if limit is not None and count >= limit:
            break
        doc, doc_id = _doc_for_index(raw, text_field, id_field)
        text = doc["description_natural"]
        vec = embeddings.embed_query(text)
        doc["vector_embedding_text"] = text
        os_id = doc_id or f"doc_{i}"
        opensearch_id = index_document(
            doc=doc,
            embedding=vec,
            doc_id=os_id,
            client=client,
            index_name=index_name,
        )
        save_document_id(opensearch_id, doc.get("violation_id", os_id))
        count += 1
    return count


def load_knowledge(
    source: str,
    path: str | Path,
    **kwargs: Any,
) -> int:
    """
    Load knowledge into the vector DB.

    - source == "violations": path to a JSON file (array of violation objects).
    - source == "jsonl": path to a JSONL file; optional text_field (default "text"),
      id_field (default "citation_id"), limit.

    Returns number of documents indexed.
    """
    path = Path(path)
    if source == "violations":
        return ingest_violations_file(path, **kwargs)
    if source == "jsonl":
        return ingest_jsonl(path, **kwargs)
    raise ValueError(f"Unknown source: {source}. Use 'violations' or 'jsonl'.")
