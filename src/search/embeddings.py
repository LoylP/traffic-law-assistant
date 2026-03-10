# -*- coding: utf-8 -*-
"""OpenAI embeddings via LangChain (from config)."""

from __future__ import annotations

from langchain_openai import OpenAIEmbeddings

from src.config import get_settings


def get_embeddings() -> OpenAIEmbeddings:
    """Build OpenAI embeddings using config (model from settings)."""
    s = get_settings()
    kwargs = {
        "model": s.embedding_model,
        "openai_api_key": s.api_key,
    }
    if s.base_url:
        kwargs["openai_api_base"] = s.base_url
    return OpenAIEmbeddings(**kwargs)
