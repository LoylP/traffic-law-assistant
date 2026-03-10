# -*- coding: utf-8 -*-
"""
Load knowledge into the vector DB (OpenSearch + document store).

- ingest_violations_file(path): load violations JSON (description_natural, violation_id, ...)
- ingest_jsonl(path, text_field, id_field): load any JSONL; embed text_field, index full doc
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

from src.config import get_settings
from src.search.document_store import ensure_document_table, save_document_id
from src.search.embeddings import get_embeddings
from src.search.opensearch_client import ensure_index, get_opensearch_client, index_document


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
        text = (doc.get("description_natural") or "").strip() or "(no text)"
        vec = embeddings.embed_query(text)
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
