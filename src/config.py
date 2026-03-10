# -*- coding: utf-8 -*-
"""Pydantic config loaded from environment."""

from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    """Application settings loaded from .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI
    base_url: str = Field(alias="BASE_URL", default="")
    api_key: str = Field(alias="API_KEY", default="")
    model: str = Field(alias="MODEL", default="gpt-4.1-mini")
    temperature: float = Field(alias="TEMPERATURE", default=0.0)
    embedding_model: str = Field(alias="EMBEDDING_MODEL", default="text-embedding-3-small")

    # OpenSearch
    opensearch_url: str = Field(alias="OPENSEARCH_URL", default="http://localhost:9200")
    opensearch_index: str = Field(alias="OPENSEARCH_INDEX", default="legal_corpus")
    opensearch_username: str = Field(alias="OPENSEARCH_USERNAME", default="")
    opensearch_password: str = Field(alias="OPENSEARCH_PASSWORD", default="")
    opensearch_ssl_verify: bool = Field(alias="OPENSEARCH_SSL_VERIFY", default=True)
    # OpenSearch request/read timeout in seconds (default 10; increase if remote cluster is slow)
    opensearch_timeout: int = Field(alias="OPENSEARCH_TIMEOUT", default=30)

    # Search: window = k-NN candidates before rerank; top_k = final results after rerank
    traffic_law_index: str = Field(alias="TRAFFIC_LAW_INDEX", default="traffic_law_index")
    search_window_size: int = Field(alias="SEARCH_WINDOW_SIZE", default=50)
    top_k: int = Field(alias="TOP_K", default=15)
    reranker_model: str = Field(
        alias="RERANKER_MODEL",
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
    )
    hf_token: str = Field(alias="HF_TOKEN", default="")
    # OpenSearch search pipeline for native rerank (created automatically if model available; set empty to disable)
    search_pipeline: str = Field(alias="SEARCH_PIPELINE", default="rerank_pipeline")
    # OpenSearch ML model ID for rerank (optional; if set, use it; else auto-load via getLLMModel-style search/register/deploy)
    opensearch_rerank_model_id: str = Field(alias="OPENSEARCH_RERANK_MODEL_ID", default="")
    # OpenSearch ML model name for auto-load (search/register); same as Go when not set
    opensearch_rerank_model_name: str = Field(
        alias="OPENSEARCH_RERANK_MODEL_NAME",
        default="huggingface/cross-encoders/ms-marco-MiniLM-L-6-v2",
    )

    # SQLite document table (for storing OpenSearch doc ids)
    sqlite_document_db: str = Field(
        alias="SQLITE_DOCUMENT_DB",
        default="data/document_ids.db",
    )

    # Contexted-text cache: JSON file with key = input hash, value = contexted text
    contexted_text_cache: str = Field(
        alias="CONTEXTED_TEXT_CACHE",
        default="data/contexted_text_cache.json",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

# Export HF token for Hugging Face Hub (model downloads, higher rate limits).
# Both names are used by different HF libraries.
_token = get_settings().hf_token
if _token:
    os.environ["HF_TOKEN"] = _token
    os.environ["HUGGING_FACE_HUB_TOKEN"] = _token
