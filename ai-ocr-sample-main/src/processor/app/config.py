"""
Configuration settings for the document processor service.
"""
import os
from typing import List, Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service settings
    LOG_LEVEL: str = "INFO"

    # Database settings
    DATABASE_URL: str

    # Redis settings
    REDIS_URL: str

    # MinIO settings
    MINIO_URL: str
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_BUCKET: str = "documents"

    # Document processing settings
    PROCESSOR_WORKERS: int = 2
    TEMP_DIR: str = "/tmp/ai-ocr"

    # LLM settings
    MODEL_NAME: str = "gpt-4o"
    MODEL_TEMPERATURE: float = 0.1
    MODEL_API_KEY: str

    # Processing settings
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 5  # seconds

    class Config:
        """Pydantic configuration."""
        env_file = ".env.local"
        case_sensitive = True


# Initialize settings
settings = Settings()

# Ensure temp directory exists
os.makedirs(settings.TEMP_DIR, exist_ok=True) 