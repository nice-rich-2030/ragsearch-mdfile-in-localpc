"""Index management module for file scanning and differential updates."""

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set
import logging

from .config import ScannerConfig, ChunkerConfig
from .db import FileDB, VectorStore
from .chunker import chunk_file
from .embedder import Embedder


logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of file scanning."""
    new_files: List[str]
    updated_files: List[str]
    deleted_files: List[str]
    unchanged_files: List[str]


@dataclass
class UpdateSummary:
    """Summary of index update."""
    added: int
    updated: int
    deleted: int
    unchanged: int
    total_chunks: int


class Indexer:
    """File indexer with differential update support."""
    
    def __init__(
        self,
        docs_dir: Path,
        file_db: FileDB,
        vector_store: VectorStore,
        embedder: Embedder,
        scanner_config: ScannerConfig,
        chunker_config: ChunkerConfig
    ):
        """
        Initialize Indexer.
        
        Args:
            docs_dir: Documents directory
            file_db: FileDB instance
            vector_store: VectorStore instance
            embedder: Embedder instance
            scanner_config: Scanner configuration
            chunker_config: Chunker configuration
        """
        self.docs_dir = Path(docs_dir)
        self.file_db = file_db
        self.vector_store = vector_store
        self.embedder = embedder
        self.scanner_config = scanner_config
        self.chunker_config = chunker_config
    
    def scan(self) -> ScanResult:
        """
        Scan documents directory and detect changes.
        
        Returns:
            ScanResult with file classifications
        """
        # Collect current files
        current_files = self._collect_files()
        current_paths = set(current_files.keys())
        
        # Get known files from database
        known_files = self.file_db.get_all_files()
        known_paths = set(known_files.keys())
        
        # Classify files
        new_files = list(current_paths - known_paths)
        deleted_files = list(known_paths - current_paths)
        existing_files = current_paths & known_paths
        
        # Check for updates in existing files (2-stage filter)
        updated_files = []
        unchanged_files = []
        
        for path in existing_files:
            current_mtime = current_files[path]
            known_record = known_files[path]
            
            # Stage 1: mtime comparison (fast)
            if current_mtime == known_record.mtime:
                unchanged_files.append(path)
                continue
            
            # Stage 2: hash comparison (slower, but only for changed mtime)
            current_hash = self._compute_hash(self.docs_dir / path)
            if current_hash == known_record.hash:
                # mtime changed but content is same
                unchanged_files.append(path)
            else:
                # Content actually changed
                updated_files.append(path)
        
        return ScanResult(
            new_files=new_files,
            updated_files=updated_files,
            deleted_files=deleted_files,
            unchanged_files=unchanged_files
        )
    
    def update(self) -> UpdateSummary:
        """
        Perform differential index update.
        
        Returns:
            UpdateSummary with statistics
        """
        logger.info("Starting index update...")
        
        # Scan for changes
        scan_result = self.scan()
        
        logger.info(
            f"Scan complete: {len(scan_result.new_files)} new, "
            f"{len(scan_result.updated_files)} updated, "
            f"{len(scan_result.deleted_files)} deleted, "
            f"{len(scan_result.unchanged_files)} unchanged"
        )
        
        # Process deletions
        for path in scan_result.deleted_files:
            logger.debug(f"Deleting: {path}")
            self.vector_store.delete_by_file(path)
            self.file_db.delete_file(path)
        
        # Process new and updated files
        files_to_process = scan_result.new_files + scan_result.updated_files
        
        for path in files_to_process:
            try:
                self._process_file(path, is_update=(path in scan_result.updated_files))
            except Exception as e:
                logger.error(f"Failed to process {path}: {e}")
        
        # Get total chunks
        total_chunks = self.vector_store.count()
        
        summary = UpdateSummary(
            added=len(scan_result.new_files),
            updated=len(scan_result.updated_files),
            deleted=len(scan_result.deleted_files),
            unchanged=len(scan_result.unchanged_files),
            total_chunks=total_chunks
        )
        
        logger.info(
            f"Index update complete: {summary.added} added, "
            f"{summary.updated} updated, {summary.deleted} deleted, "
            f"{summary.total_chunks} total chunks"
        )
        
        return summary
    
    def _process_file(self, relative_path: str, is_update: bool = False):
        """
        Process a single file (new or updated).
        
        Args:
            relative_path: Relative path from docs_dir
            is_update: Whether this is an update (vs new file)
        """
        full_path = self.docs_dir / relative_path
        
        logger.debug(f"Processing: {relative_path}")
        
        # Delete old chunks if updating
        if is_update:
            self.vector_store.delete_by_file(relative_path)
        
        # Read file content
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            with open(full_path, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Chunk the content
        chunks = chunk_file(Path(relative_path), content, self.chunker_config)
        
        if not chunks:
            logger.warning(f"No chunks generated for {relative_path}")
            return
        
        logger.debug(f"  Generated {len(chunks)} chunks")
        
        # Generate embeddings
        texts = [chunk.content for chunk in chunks]
        embeddings = self.embedder.embed_texts(texts)
        
        # Add to vector store
        self.vector_store.add_chunks(relative_path, chunks, embeddings)
        
        # Update file database
        file_hash = self._compute_hash(full_path)
        file_mtime = full_path.stat().st_mtime
        self.file_db.upsert_file(relative_path, file_hash, file_mtime)
    
    def _collect_files(self) -> Dict[str, float]:
        """
        Collect all target files in docs_dir.
        
        Returns:
            Dictionary mapping relative path to mtime
        """
        files = {}
        
        for ext in self.scanner_config.file_extensions:
            for file_path in self.docs_dir.rglob(f"*{ext}"):
                # Skip excluded directories
                if self._is_excluded(file_path):
                    continue
                
                relative_path = str(file_path.relative_to(self.docs_dir))
                files[relative_path] = file_path.stat().st_mtime
        
        return files
    
    def _is_excluded(self, path: Path) -> bool:
        """
        Check if path should be excluded.
        
        Args:
            path: Path to check
            
        Returns:
            True if path should be excluded
        """
        parts = path.parts
        for exclude_dir in self.scanner_config.exclude_dirs:
            if exclude_dir in parts:
                return True
        return False
    
    def _compute_hash(self, path: Path) -> str:
        """
        Compute SHA256 hash of file.
        
        Args:
            path: File path
            
        Returns:
            SHA256 hash as hex string
        """
        sha256 = hashlib.sha256()
        
        with open(path, 'rb') as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha256.update(chunk)
        
        return sha256.hexdigest()
