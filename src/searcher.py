"""Semantic search module."""

from dataclasses import dataclass
from typing import List
import logging

from .embedder import Embedder
from .db import VectorStore


logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result with metadata."""
    file_path: str
    content: str
    heading: str
    score: float
    chunk_index: int


class Searcher:
    """Semantic search engine."""
    
    def __init__(self, embedder: Embedder, vector_store: VectorStore):
        """
        Initialize Searcher.
        
        Args:
            embedder: Embedder instance
            vector_store: VectorStore instance
        """
        self.embedder = embedder
        self.vector_store = vector_store
    
    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        Search for documents similar to the query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of SearchResult objects, sorted by score (descending)
        """
        # Check if index is empty
        if self.vector_store.count() == 0:
            logger.warning("Vector store is empty. No results to return.")
            return []
        
        # Generate query embedding
        query_embedding = self.embedder.embed_query(query)
        
        if not query_embedding:
            logger.error("Failed to generate query embedding")
            return []
        
        # Search in vector store
        query_results = self.vector_store.query(query_embedding, top_k)
        
        # Convert to SearchResult with score conversion
        search_results = []
        for result in query_results:
            # Convert distance to similarity score
            # For cosine distance: similarity = 1 - distance
            score = 1.0 - result.distance
            
            search_results.append(SearchResult(
                file_path=result.file_path,
                content=result.content,
                heading=result.heading,
                score=score,
                chunk_index=result.chunk_index
            ))
        
        return search_results
