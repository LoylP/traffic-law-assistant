from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from src.settings import LLMType, settings


def get_llm_client() -> ChatOpenAI | ChatOllama:
    """
    Get the LLM client based on the settings.
    Args:
        - settings: The settings object.
    Returns:
        - The LLM client.
    """
    
    if settings.llm_type == LLMType.OPENAI:
        return ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_url,
        )
    if settings.llm_type == LLMType.OLLAMA:
        return ChatOllama(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_api_url
        )
    raise ValueError(f"Unsupported LLM type: {settings.llm_type}")


