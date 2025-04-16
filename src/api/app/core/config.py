"""
Configuration settings for the AI-OCR API service.
"""
import os
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, BaseSettings, validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API settings
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = "development_secret_key"

    # Database settings
    DATABASE_URL: str

    # Redis settings
    REDIS_URL: str

    # MinIO settings
    MINIO_URL: str
    MINIO_ROOT_USER: str
    MINIO_ROOT_PASSWORD: str
    MINIO_BUCKET: str = "documents"

    # Document processor settings
    PROCESSOR_URL: str

    # Document settings
    MAX_DOCUMENT_SIZE: int = 50000000  # 50MB in bytes
    ALLOWED_EXTENSIONS: List[str] = ["xlsx", "xls", "csv"]

    @validator("ALLOWED_EXTENSIONS", pre=True)
    def split_extensions(cls, v):
        """Split comma-separated extensions into a list."""
        if isinstance(v, str):
            return [ext.strip() for ext in v.split(",")]
        return v

    # Security settings
    CORS_ORIGINS: List[AnyHttpUrl] = []

    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str) and not v.startswith("["):
            return [origin.strip() for origin in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    TOKEN_EXPIRY: int = 86400  # 24 hours in seconds

    class Config:
        """Pydantic configuration."""
        env_file = ".env.local"
        case_sensitive = True


# Initialize settings
settings = Settings() 