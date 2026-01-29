"""Database layer for file metadata and vector storage."""

import sqlite3
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import chromadb

from .config import ChromaDBConfig
from .chunker import Chunk


logger = logging.getLogger(__name__)


@dataclass
class FileRecord:
    """File metadata record."""
    path: str
    hash: str
    mtime: float


@dataclass
class QueryResult:
    """Vector search result."""
    file_path: str
    content: str
    heading: str
    distance: float
    chunk_index: int


class FileDB:
    """SQLite database for file metadata management."""
    
    def __init__(self, db_path: Path):
        """
        Initialize FileDB.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(db_path))
        self._create_tables()
    
    def _create_tables(self):
        """Create database tables if they don't exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                hash TEXT NOT NULL,
                mtime REAL NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def get_all_files(self) -> Dict[str, FileRecord]:
        """
        Get all file records.
        
        Returns:
            Dictionary mapping file path to FileRecord
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT path, hash, mtime FROM files")
        
        records = {}
        for row in cursor.fetchall():
            records[row[0]] = FileRecord(
                path=row[0],
                hash=row[1],
                mtime=row[2]
            )
        
        return records
    
    def upsert_file(self, path: str, hash: str, mtime: float):
        """
        Insert or update file record.
        
        Args:
            path: Relative file path
            hash: SHA256 hash
            mtime: Modification time
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO files (path, hash, mtime, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(path) DO UPDATE SET
                hash = excluded.hash,
                mtime = excluded.mtime,
                updated_at = CURRENT_TIMESTAMP
        """, (path, hash, mtime))
        self.conn.commit()
    
    def delete_file(self, path: str):
        """
        Delete file record.
        
        Args:
            path: Relative file path
        """
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM files WHERE path = ?", (path,))
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()


class VectorStore:
    """ChromaDB vector store for document chunks."""
    
    def __init__(self, persist_dir: Path, config: ChromaDBConfig):
        """
        Initialize VectorStore.
        
        Args:
            persist_dir: Directory for ChromaDB persistence
            config: ChromaDB configuration
        """
        self.persist_dir = persist_dir
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.config = config

        # Initialize ChromaDB client (simplified for ChromaDB 1.4.1)
        logger.debug(f"Initializing ChromaDB client at {persist_dir}")
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        logger.debug("ChromaDB client initialized")

        # Get or create collection (simplified metadata for ChromaDB 1.4.1)
        logger.debug(f"Getting or creating collection: {config.collection_name}")
        self.collection = self.client.get_or_create_collection(
            name=config.collection_name
        )
        logger.debug(f"Collection ready: {config.collection_name}")
    
    def add_chunks(
        self,
        file_path: str,
        chunks: List[Chunk],
        embeddings: List[List[float]]
    ):
        """
        Add chunks with embeddings to the collection.

        Args:
            file_path: Relative file path
            chunks: List of Chunk objects
            embeddings: List of embedding vectors
        """
        if not chunks or not embeddings:
            return

        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Chunks and embeddings length mismatch: "
                f"{len(chunks)} vs {len(embeddings)}"
            )

        logger.debug(f"    Preparing {len(chunks)} chunks for ChromaDB...")
        ids = [f"{file_path}::chunk_{chunk.chunk_index}" for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "file_path": file_path,
                "chunk_index": chunk.chunk_index,
                "heading": chunk.heading
            }
            for chunk in chunks
        ]

        logger.debug(f"    Calling ChromaDB collection.add()...")
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        logger.debug(f"    ChromaDB collection.add() completed")
    
    def delete_by_file(self, file_path: str):
        """
        Delete all chunks for a specific file.
        
        Args:
            file_path: Relative file path
        """
        # Get existing chunks for this file
        try:
            existing = self.collection.get(
                where={"file_path": file_path}
            )
            
            if existing and existing['ids']:
                self.collection.delete(ids=existing['ids'])
        except Exception:
            # If no chunks exist, that's fine
            pass
    
    def query(
        self, 
        query_embedding: List[float], 
        top_k: int
    ) -> List[QueryResult]:
        """
        Search for similar chunks.
        
        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            
        Returns:
            List of QueryResult objects
        """
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )
        
        query_results = []
        
        if results and results['ids'] and results['ids'][0]:
            for i in range(len(results['ids'][0])):
                metadata = results['metadatas'][0][i]
                query_results.append(QueryResult(
                    file_path=metadata['file_path'],
                    content=results['documents'][0][i],
                    heading=metadata.get('heading', ''),
                    distance=results['distances'][0][i],
                    chunk_index=metadata['chunk_index']
                ))
        
        return query_results
    
    def count(self) -> int:
        """
        Get total number of chunks in the collection.
        
        Returns:
            Number of chunks
        """
        return self.collection.count()
