# ENV Config:
BASE_URL=xxxx/v1 # OpenAI API URL
API_KEY=sk-lcfvxz # OpenAI API Key
MODEL=gpt-4.1-mini # OpenAI Model
TEMPERATURE=0.0
EMBEDDING_MODEL=text-embedding-3-small # OpenAI Embedding Model 
OPENSEARCH_URL=http://xxxxx:9200 # OpenSearch URL
OPENSEARCH_INDEX=legal_corpus # OpenSearch Index
OPENSEARCH_USERNAME="" # OpenSearch Username
OPENSEARCH_PASSWORD="" # OpenSearch Password
OPENSEARCH_SSL_VERIFY=false # OpenSearch SSL Verify
SEARCH_PIPELINE= # Optional: OpenSearch search pipeline name for native rerank (if set, no in-app rerank)
TOP_K=5
TRAFFIC_LAW_INDEX=traffic_law_index
SQLITE_DOCUMENT_DB=data/document_ids.db

# OpenSearch Config:
- Source docs: violations_300.json
  - Embeddings text: "description_natural"
  - Embeddings model: load from config settings (Pydantic BaseModel)
  - Reranker: load from config settings (Pydantic BaseModel), huggingface model (huggingface/cross-encoders/ms-marco-MiniLM-L-6-v2). Regiter this model to opensearch.
  - Index name: "traffic_law_index"
  - Top k: 5 (from config settings)

- Interfaces:
  - Text to embeddings:
    - Get embeddings from OpenAI with config settings model (langchain_openai.embeddings.base.OpenAIEmbeddings)
  - Insert full document into opensearch with embeddings
    - ```json
    {
        "description_natural": "...",
        "normalized_violation": "...",
        "vehicle_type": "...",
        "context_condition": "...",
        "fine_min": ...,
        "fine_max": ...,
        "additional_sanctions": "...",
        "legal_basis": "...",
        "confidence_label": "...",
        "violation_id": "..."
    }
    ```
    - Save document id into SQLite document table (managed with SQLAlchemy).

- Search:
  - Search by text:
    - Get embeddings from OpenAI with config settings model (langchain_openai.embeddings.base.OpenAIEmbeddings)
    - Query text to embeddings
    - Search with embeddings; then rerank: either via OpenSearch (set SEARCH_PIPELINE to a pipeline that uses an ml_opensearch rerank model and document_fields: ["description_natural"]) or in-app with huggingface cross-encoder (huggingface/cross-encoders/ms-marco-MiniLM-L-6-v2).
  - Return top k documents with score.
  - If index does not exist (e.g. before first ingest), search returns [] (no 500).

- Make some test scripts to test the search engine.

# Load knowledge into vector DB
- **Violations (JSON)**: `ingest_violations_file(path)` or `load_knowledge("violations", path)` — expects array of objects with `description_natural`, `violation_id`, etc.
- **JSONL (e.g. law corpus)**: `ingest_jsonl(path, text_field="text", id_field="citation_id")` or `load_knowledge("jsonl", path, text_field="text", id_field="citation_id")` — each line one JSON object; `text_field` is embedded, full doc stored.
- **API**: `POST /api/ingest` with body `{"source": "violations"}` or `{"source": "jsonl", "path": "data/structured/law_corpus.jsonl"}` (paths under `data/structured/` only).

# OpenSearch native rerank (optional)
1. Register a cross-encoder model in OpenSearch (ML plugin). Get the model_id.
2. Create a search pipeline with rerank processor and `document_fields`: `["description_natural"]`.
3. Set `SEARCH_PIPELINE=<pipeline_name>` in .env. Search will use it and skip in-app rerank.