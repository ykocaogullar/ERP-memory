"""
Services package for ERP Memory API.
"""

from .embeddings import (
    EmbeddingService,
    get_embedding_service,
    reset_embedding_service,
)

__version__ = "0.1.0"

__all__ = [
    "EmbeddingService",
    "get_embedding_service",
    "reset_embedding_service",
]

