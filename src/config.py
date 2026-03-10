# -*- coding: utf-8 -*-
"""Pydantic config loaded from environment."""

from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Search (doc says index name "traffic_law_index" and top k: 5)
    traffic_law_index: str = Field(alias="TRAFFIC_LAW_INDEX", default="traffic_law_index")
    top_k: int = Field(alias="TOP_K", default=5)
    reranker_model: str = Field(
        alias="RERANKER_MODEL",
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
    )
    # OpenSearch search pipeline for native rerank (optional; if set, no Python rerank)
    search_pipeline: str = Field(alias="SEARCH_PIPELINE", default="")

    # SQLite document table (for storing OpenSearch doc ids)
    sqlite_document_db: str = Field(
        alias="SQLITE_DOCUMENT_DB",
        default="data/document_ids.db",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
