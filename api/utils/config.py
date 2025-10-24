"""
Configuration management using pydantic-settings

Loads configuration from environment variables and .env file
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database Configuration
    DATABASE_URL: str = Field(
        default="postgresql://erp_user:erp_password@localhost:5432/erp_db",
        description="Full database connection URL"
    )
    DB_HOST: str = Field(default="localhost", description="Database host")
    DB_PORT: int = Field(default=5432, description="Database port")
    DB_NAME: str = Field(default="erp_db", description="Database name")
    DB_USER: str = Field(default="erp_user", description="Database user")
    DB_PASSWORD: str = Field(default="erp_password", description="Database password")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key (required)")
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-3-small",
        description="OpenAI embedding model"
    )
    EMBEDDING_DIMENSION: int = Field(
        default=1536,
        description="Embedding vector dimension"
    )
    LLM_MODEL: str = Field(
        default="gpt-4o-mini",
        description="OpenAI chat model"
    )
    
    # Application Settings
    API_HOST: str = Field(default="0.0.0.0", description="API host to bind to")
    API_PORT: int = Field(default=8080, description="API port to listen on")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Memory System Configuration
    ENABLE_VECTORS: bool = Field(default=True, description="Enable vector embeddings")
    ENABLE_PII_REDACTION: bool = Field(default=True, description="Enable PII redaction")
    FTS_LANGUAGE: str = Field(default="english", description="Full-text search language")
    TRIGRAM_THRESHOLD: float = Field(default=0.3, description="Trigram similarity threshold")
    MEMORY_TTL_DAYS: int = Field(default=30, description="Default memory TTL in days")
    CONSOLIDATION_WINDOW: int = Field(default=3, description="Session window for consolidation")
    VECTOR_DIMENSIONS: int = Field(default=1536, description="Vector embedding dimensions")
    
    # Semantic Layer Configuration
    ENABLE_SEMANTIC_RELATIONSHIPS: bool = Field(
        default=True,
        description="Enable semantic relationship extraction"
    )
    ENTITY_EMBEDDING_ENABLED: bool = Field(
        default=True,
        description="Enable entity-level embeddings"
    )
    SEMANTIC_SCORE_WEIGHT: float = Field(
        default=0.2,
        description="Weight for semantic scoring in hybrid retrieval"
    )
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance"""
    return settings
