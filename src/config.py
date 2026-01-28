"""Configuration management module for RAG MCP Server."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class EmbeddingConfig:
    """Gemini Embedding API configuration."""
    model: str = "gemini-embedding-001"
    output_dimensionality: int = 768
    batch_size: int = 100
    task_type_document: str = "RETRIEVAL_DOCUMENT"
    task_type_query: str = "RETRIEVAL_QUERY"


@dataclass
class ChunkerConfig:
    """Text chunking configuration."""
    max_chunk_chars: int = 3000
    min_chunk_chars: int = 50
    heading_levels: list[int] = field(default_factory=lambda: [1, 2, 3])


@dataclass
class ChromaDBConfig:
    """ChromaDB configuration."""
    collection_name: str = "documents"
    hnsw_space: str = "cosine"
    hnsw_construction_ef: int = 200
    hnsw_search_ef: int = 100
    hnsw_M: int = 16


@dataclass
class SearchConfig:
    """Search configuration."""
    default_top_k: int = 5


@dataclass
class RetryConfig:
    """API retry configuration."""
    max_retries: int = 3
    base_delay: float = 1.0
    backoff_factor: float = 2.0


@dataclass
class ScannerConfig:
    """File scanner configuration."""
    file_extensions: list[str] = field(default_factory=lambda: [".md", ".txt"])
    exclude_dirs: list[str] = field(default_factory=lambda: [
        ".rag-index", "data", ".git", "__pycache__", "node_modules"
    ])


@dataclass
class AppConfig:
    """Application configuration."""
    embedding: EmbeddingConfig
    chunker: ChunkerConfig
    chromadb: ChromaDBConfig
    search: SearchConfig
    retry: RetryConfig
    scanner: ScannerConfig


def load_config(config_path: Optional[Path] = None, docs_dir: Optional[Path] = None) -> AppConfig:
    """
    Load configuration from YAML file.
    
    Search order:
    1. config_path (if provided)
    2. docs_dir/config.yaml (if docs_dir provided)
    3. project_root/config.yaml
    
    If no config file is found, returns default configuration.
    
    Args:
        config_path: Explicit path to config file
        docs_dir: Documents directory to search for config
        
    Returns:
        AppConfig instance with loaded or default configuration
    """
    # Determine config file path
    yaml_path = None
    
    if config_path and config_path.exists():
        yaml_path = config_path
    elif docs_dir:
        candidate = docs_dir / "config.yaml"
        if candidate.exists():
            yaml_path = candidate
    
    # Fallback to project root
    if not yaml_path:
        project_root = Path(__file__).parent.parent
        candidate = project_root / "config.yaml"
        if candidate.exists():
            yaml_path = candidate
    
    # Load YAML or use defaults
    config_dict = {}
    if yaml_path:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            config_dict = yaml.safe_load(f) or {}
    
    # Create config objects with defaults
    embedding_cfg = EmbeddingConfig(
        **config_dict.get('embedding', {})
    )
    
    chunker_cfg = ChunkerConfig(
        **{k: v for k, v in config_dict.get('chunker', {}).items() 
           if k != 'heading_levels'}
    )
    if 'heading_levels' in config_dict.get('chunker', {}):
        chunker_cfg.heading_levels = config_dict['chunker']['heading_levels']
    
    chromadb_cfg = ChromaDBConfig(
        **config_dict.get('chromadb', {})
    )
    
    search_cfg = SearchConfig(
        **config_dict.get('search', {})
    )
    
    retry_cfg = RetryConfig(
        **config_dict.get('retry', {})
    )
    
    scanner_cfg = ScannerConfig(
        **{k: v for k, v in config_dict.get('scanner', {}).items() 
           if k not in ['file_extensions', 'exclude_dirs']}
    )
    if 'file_extensions' in config_dict.get('scanner', {}):
        scanner_cfg.file_extensions = config_dict['scanner']['file_extensions']
    if 'exclude_dirs' in config_dict.get('scanner', {}):
        scanner_cfg.exclude_dirs = config_dict['scanner']['exclude_dirs']
    
    return AppConfig(
        embedding=embedding_cfg,
        chunker=chunker_cfg,
        chromadb=chromadb_cfg,
        search=search_cfg,
        retry=retry_cfg,
        scanner=scanner_cfg
    )
