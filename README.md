Hệ thống hỏi đáp Luật Giao thông theo ngữ nghĩa

## Search engine (traffic violations)

- **Config**: `.env` (see `docs.md`). Pydantic settings in `src/config.py`.
- **Index**: OpenSearch index `traffic_law_index` with k-NN on embeddings of `description_natural` (OpenAI `text-embedding-3-small`). Rerank: set `SEARCH_PIPELINE` to use OpenSearch native rerank, or in-app cross-encoder.
- **Document store**: SQLAlchemy (table `document`: opensearch_id, violation_id); DB path from `SQLITE_DOCUMENT_DB`.
- **Load knowledge (vector DB)**:
  - **CLI**: `python scripts/ingest_violations.py` — loads `data/structured/violations_300.json`.
  - **Code**: `from src.search.ingest import load_knowledge; load_knowledge("violations", "data/structured/violations_300.json")` or `load_knowledge("jsonl", "data/structured/law_corpus.jsonl", text_field="text", id_field="citation_id")`.
  - **API**: `POST /api/ingest` with body `{"source": "violations"}` or `{"source": "jsonl", "path": "data/structured/law_corpus.jsonl"}` (paths under `data/structured/` only).
- **Search**: `from src.search import SearchService; SearchService().search("vượt đèn đỏ")` or CLI: `python scripts/test_search.py "vượt đèn đỏ"`.
- **Web UI**: `uvicorn src.api.main:app --reload` then open http://127.0.0.1:8000 to test search in the browser.
- **Tests**: `pytest tests/test_search_engine.py -v`. Integration: `python scripts/test_search_integration.py` (requires OpenSearch + ingest).
