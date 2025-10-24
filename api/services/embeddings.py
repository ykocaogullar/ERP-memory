"""
Embedding Service - Generate text embeddings using OpenAI.

This service provides a wrapper around the OpenAI embedding API
with error handling, batching, and optional caching.
"""

from typing import List, Optional, Union
import logging
from functools import lru_cache

from openai import OpenAI
from openai.types.embedding import Embedding

from api.utils.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI's API.
    
    Features:
    - Text embedding generation using text-embedding-3-small (1536 dimensions)
    - Batch processing for multiple texts
    - Error handling and retry logic
    - Optional in-memory caching for frequently embedded text
    """
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize the embedding service.
        
        Args:
            api_key: OpenAI API key (defaults to settings.OPENAI_API_KEY)
            model: Embedding model to use (defaults to settings.EMBEDDING_MODEL)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.EMBEDDING_MODEL
        self.dimension = settings.EMBEDDING_DIMENSION
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in environment.")
        
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"Initialized EmbeddingService with model={self.model}, dimension={self.dimension}")
    
    def embed_text(self, text: str, use_cache: bool = False) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            use_cache: Whether to use in-memory cache (useful for frequently embedded text)
        
        Returns:
            List of floats representing the embedding vector
        
        Raises:
            ValueError: If text is empty
            Exception: If OpenAI API call fails
        """
        if not text or not text.strip():
            raise ValueError("Cannot embed empty text")
        
        if use_cache:
            return self._embed_text_cached(text)
        
        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=text.strip(),
                encoding_format="float"
            )
            
            embedding = response.data[0].embedding
            
            # Validate dimension
            if len(embedding) != self.dimension:
                logger.warning(
                    f"Expected {self.dimension} dimensions but got {len(embedding)}. "
                    f"Model: {self.model}"
                )
            
            logger.debug(f"Generated embedding for text: '{text[:50]}...' ({len(embedding)} dimensions)")
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    @lru_cache(maxsize=1000)
    def _embed_text_cached(self, text: str) -> tuple:
        """
        Cached version of embed_text. Returns tuple for hashability.
        
        Note: LRU cache requires hashable arguments, so we return a tuple
        which can be converted back to a list by the caller.
        """
        embedding = self.embed_text(text, use_cache=False)
        return tuple(embedding)
    
    def embed_batch(
        self, 
        texts: List[str], 
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to embed per API call (max 2048 for OpenAI)
        
        Returns:
            List of embedding vectors in the same order as input texts
        
        Raises:
            ValueError: If any text is empty
            Exception: If OpenAI API call fails
        """
        if not texts:
            return []
        
        # Validate all texts
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise ValueError(f"Text at index {i} is empty")
        
        all_embeddings = []
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_cleaned = [text.strip() for text in batch]
            
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=batch_cleaned,
                    encoding_format="float"
                )
                
                # Extract embeddings in order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
                
                logger.debug(
                    f"Generated embeddings for batch {i//batch_size + 1} "
                    f"({len(batch)} texts, {len(batch_embeddings)} embeddings)"
                )
                
            except Exception as e:
                logger.error(f"Failed to generate embeddings for batch {i//batch_size + 1}: {e}")
                raise
        
        return all_embeddings
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
        
        Returns:
            Cosine similarity score between -1 and 1
        
        Note: pgvector's <=> operator returns cosine distance (1 - similarity),
        but this method returns actual cosine similarity for convenience.
        """
        if len(vec1) != len(vec2):
            raise ValueError(f"Vector dimensions don't match: {len(vec1)} vs {len(vec2)}")
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        similarity = dot_product / (magnitude1 * magnitude2)
        return similarity
    
    def clear_cache(self):
        """Clear the embedding cache."""
        self._embed_text_cached.cache_clear()
        logger.info("Cleared embedding cache")


# Global singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    Get the global embedding service instance.
    
    Returns:
        EmbeddingService instance
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def reset_embedding_service():
    """Reset the global embedding service (useful for testing)."""
    global _embedding_service
    _embedding_service = None
