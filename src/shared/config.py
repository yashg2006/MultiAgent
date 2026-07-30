"""
Global project configuration and settings loader.
"""

import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "MultiAgentAISystem"
    environment: str = os.getenv("ENV", "development")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    class Config:
        env_file = ".env"

settings = Settings()
