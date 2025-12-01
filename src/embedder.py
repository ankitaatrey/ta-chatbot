"""Embedding generation with support for multiple backends."""

from typing import List, Optional
import logging
import numpy as np

from src.config import config
from src.utils.logging_setup import get_logger

logger = get_logger(__name__)


class Embedder:
    """Wrapper for embedding generation."""
    
    def __init__(self, model_name: Optional[str] = None, use_openai: bool = False):
        """
        Initialize the embedder.
        
        Args:
            model_name: Model name (for sentence-transformers or OpenAI)
            use_openai: Whether to use OpenAI embeddings
        """
        self.use_openai = use_openai and config.openai_api_key is not None
        self.model_name = model_name
        self.model = None
        
        if self.use_openai:
            self._init_openai()
        else:
            self._init_sentence_transformers()
    
    def _init_openai(self):
        """Initialize OpenAI embeddings."""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=config.openai_api_key)
            self.model_name = self.model_name or "text-embedding-3-small"
            logger.info(f"Initialized OpenAI embeddings: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI embeddings: {e}")
            logger.info("Falling back to sentence-transformers")
            self.use_openai = False
            self._init_sentence_transformers()
    
    def _init_sentence_transformers(self):
        """Initialize sentence-transformers embeddings."""
        try:
            from sentence_transformers import SentenceTransformer
            self.model_name = self.model_name or "sentence-transformers/all-MiniLM-L6-v2"
            logger.info(f"Loading sentence-transformers model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Successfully loaded sentence-transformers model")
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers model: {e}")
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of documents.
        
        Args:
            texts: List of text strings
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        if self.use_openai:
            return self._embed_openai(texts)
        else:
            return self._embed_sentence_transformers(texts)
    
    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single query.
        
        Args:
            text: Query text
            
        Returns:
            Embedding vector
        """
        if self.use_openai:
            embeddings = self._embed_openai([text])
            return embeddings[0] if embeddings else []
        else:
            return self._embed_sentence_transformers([text])[0]
    
    def _embed_openai(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        try:
            # Process in batches to avoid rate limits
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.model_name
                )
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)
            
            return all_embeddings
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise
    
    def _embed_sentence_transformers(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using sentence-transformers."""
        try:
            embeddings = self.model.encode(
                texts,
                show_progress_bar=len(texts) > 10,
                convert_to_numpy=True,
                batch_size=32
            )
            # Convert to list of lists
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Sentence-transformers embedding failed: {e}")
            raise
    
    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        if self.use_openai:
            # Common OpenAI embedding dimensions
            if "text-embedding-3-small" in self.model_name:
                return 1536
            elif "text-embedding-3-large" in self.model_name:
                return 3072
            else:
                return 1536  # Default
        else:
            # Get from model
            if self.model:
                return self.model.get_sentence_embedding_dimension()
            return 384  # Default for MiniLM


def get_embedder(use_openai: Optional[bool] = None) -> Embedder:
    """
    Get an embedder instance based on configuration.
    
    Args:
        use_openai: Override config to use OpenAI (if None, uses config)
        
    Returns:
        Embedder instance
    """
    if use_openai is None:
        # Check if we should use local embeddings (default: True for cost savings)
        if config.use_local_embeddings:
            use_openai = False
        else:
            use_openai = not config.local and config.openai_api_key is not None
    
    return Embedder(use_openai=use_openai)

