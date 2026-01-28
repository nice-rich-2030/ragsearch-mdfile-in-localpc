"""Embedding generation module using Gemini API."""

import os
import time
from typing import List
import logging

try:
    from google import genai
    from google.genai import types
except ImportError:
    import google.generativeai as genai
    types = None

from .config import EmbeddingConfig, RetryConfig


logger = logging.getLogger(__name__)


class Embedder:
    """Gemini Embedding API client."""
    
    def __init__(self, embedding_config: EmbeddingConfig, retry_config: RetryConfig):
        """
        Initialize Embedder.
        
        Args:
            embedding_config: Embedding configuration
            retry_config: Retry configuration
        """
        self.embedding_config = embedding_config
        self.retry_config = retry_config
        
        # Get API key from environment
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY or GOOGLE_API_KEY environment variable must be set"
            )
        
        # Initialize client
        try:
            # Try new google-genai SDK
            self.client = genai.Client(api_key=api_key)
            self.use_new_sdk = True
        except Exception:
            # Fallback to old google-generativeai SDK
            genai.configure(api_key=api_key)
            self.use_new_sdk = False
    
    def embed_texts(
        self, 
        texts: List[str], 
        task_type: str = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            task_type: Task type (RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY)
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        if task_type is None:
            task_type = self.embedding_config.task_type_document
        
        all_embeddings = []
        batch_size = self.embedding_config.batch_size
        
        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = self._embed_batch_with_retry(batch, task_type)
            all_embeddings.extend(batch_embeddings)
        
        return all_embeddings
    
    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a query.
        
        Args:
            query: Query text
            
        Returns:
            Embedding vector
        """
        embeddings = self.embed_texts(
            [query], 
            task_type=self.embedding_config.task_type_query
        )
        return embeddings[0] if embeddings else []
    
    def _embed_batch_with_retry(
        self, 
        texts: List[str], 
        task_type: str
    ) -> List[List[float]]:
        """
        Embed a batch of texts with retry logic.
        
        Args:
            texts: Batch of texts
            task_type: Task type
            
        Returns:
            List of embedding vectors
        """
        for attempt in range(self.retry_config.max_retries):
            try:
                return self._embed_batch(texts, task_type)
            except Exception as e:
                if attempt == self.retry_config.max_retries - 1:
                    logger.error(f"Failed to embed batch after {self.retry_config.max_retries} attempts: {e}")
                    raise
                
                delay = self.retry_config.base_delay * (
                    self.retry_config.backoff_factor ** attempt
                )
                logger.warning(
                    f"Embedding attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
        
        return []
    
    def _embed_batch(self, texts: List[str], task_type: str) -> List[List[float]]:
        """
        Embed a batch of texts using Gemini API.
        
        Args:
            texts: Batch of texts
            task_type: Task type
            
        Returns:
            List of embedding vectors
        """
        if self.use_new_sdk:
            # New google-genai SDK
            config = types.EmbedContentConfig(
                task_type=task_type,
                output_dimensionality=self.embedding_config.output_dimensionality
            )
            
            result = self.client.models.embed_content(
                model=self.embedding_config.model,
                contents=texts,
                config=config
            )
            
            return [embedding.values for embedding in result.embeddings]
        else:
            # Old google-generativeai SDK
            result = genai.embed_content(
                model=f"models/{self.embedding_config.model}",
                content=texts,
                task_type=task_type,
                output_dimensionality=self.embedding_config.output_dimensionality
            )
            
            if isinstance(result['embedding'][0], list):
                return result['embedding']
            else:
                return [result['embedding']]
