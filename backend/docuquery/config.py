import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, model_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "DocuQuery"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"

    # Security & Auth
    SECRET_KEY: str = Field(
        default="docuquery-insecure-secret-key-change-in-production-1234567890",
        description="Secret key for JWT generation",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+psycopg2://docuquery:docuquery_secret@localhost:5432/docuquery",
        description="Database connection string",
    )

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # Object Storage
    STORAGE_BACKEND: str = "s3"  # "s3" or "filesystem"
    STORAGE_LOCAL_DIR: str = "./data/storage"
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "docuquery-documents"
    S3_REGION_NAME: str = "us-east-1"
    S3_SECURE: bool = False

    # Document upload limits
    MAX_UPLOAD_SIZE_BYTES: int = 25 * 1024 * 1024  # 25 MB
    MAX_DOCUMENT_PAGES: int = 500
    USER_STORAGE_LIMIT_BYTES: int = 100 * 1024 * 1024  # 100 MB per user

    # Chunking & Embedding
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    CHUNK_EXTRACTION_VERSION: str = "v2"
    EMBEDDING_PROVIDER: str = "mock"  # "mock", "gemini", "openai", "ollama"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIM: int = 1536

    # LLM generation
    LLM_PROVIDER: str = "mock"  # "mock", "gemini", "openai", "ollama"
    LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # RAG Retrieval Settings
    RAG_TOP_K: int = 5
    RAG_SIMILARITY_THRESHOLD: float = 0.20
    RAG_HYBRID_RETRIEVAL: bool = True
    RAG_HYBRID_ALPHA: float = 0.50
    RAG_RERANKING_ENABLED: bool = True
    RAG_RERANK_CANDIDATES_K: int = 15
    RAG_ABSTENTION_THRESHOLD: float = 0.25

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ]

    def get_celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.REDIS_URL

    def get_celery_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.ENVIRONMENT.lower() == "production":
            if (
                not self.SECRET_KEY
                or "insecure" in self.SECRET_KEY.lower()
                or "change-in-production" in self.SECRET_KEY.lower()
                or len(self.SECRET_KEY) < 32
            ):
                raise ValueError(
                    "Insecure SECRET_KEY detected in production environment! "
                    "A cryptographically secure key of at least 32 characters must be provided."
                )
            if self.STORAGE_BACKEND == "s3" and self.S3_SECRET_KEY == "minioadmin":
                raise ValueError("Default S3/MinIO credentials detected in production environment!")
        return self


settings = Settings()
