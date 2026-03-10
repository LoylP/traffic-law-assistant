from enum import Enum
from pydantic_settings import BaseSettings
from pydantic import Field

class LLMType(Enum):
    OPENAI = "openai"
    OLLAMA = "ollama"

class Settings(BaseSettings):
    llm_model: str = Field(default="gpt-4.1-mini", alias="MODEL")
    llm_api_key: str = Field(default="", alias="API_KEY")
    llm_api_url: str = Field(default="", alias="BASE_URL")
    llm_type: LLMType = Field(default=LLMType.OPENAI)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        populate_by_name = True
    
    
settings = Settings()