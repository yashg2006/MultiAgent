"""
Global project configuration and settings loader.
"""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "MultiAgentAISystem"
    environment: str = os.getenv("ENV", "development")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # "mock" (default, offline/deterministic) or "openai" (requires openai_api_key).
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")

    # Orchestrator retry policy (NFR-03).
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_base_delay_seconds: float = float(os.getenv("RETRY_BASE_DELAY_SECONDS", "0.5"))

    class Config:
        env_file = ".env"


settings = Settings()
