"""Reindex test-docs with updated config."""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

load_dotenv()

from src.shared.config import load_config
from src.shared.db import FileDB, VectorStore
from src.shared.embedder import Embedder
from src.shared.indexer import Indexer


def reindex_testdocs():
    """Test-docsを再インデックス"""

    docs_dir = Path("./test-docs").resolve()
    data_dir = docs_dir / ".rag-index"

    print("=" * 80)
    print("Reindex Test Docs")
    print("=" * 80)
    print(f"Docs dir: {docs_dir}")
    print(f"Data dir: {data_dir}")
    print()

    # Load config
    app_config = load_config(docs_dir=docs_dir)
    print(f"Config loaded:")
    print(f"  min_chunk_chars: {app_config.chunker.min_chunk_chars}")
    print(f"  max_chunk_chars: {app_config.chunker.max_chunk_chars}")
    print()

    # Initialize components
    file_db = FileDB(data_dir / "files.db")
    vector_store = VectorStore(data_dir / "chroma", app_config.chromadb)
    embedder = Embedder(app_config.embedding, app_config.retry)
    indexer = Indexer(
        docs_dir, file_db, vector_store, embedder,
        app_config.scanner, app_config.chunker
    )

    print("Components initialized")
    print()

    # Run indexer
    print("Running indexer...")
    summary = indexer.update()

    print()
    print("=" * 80)
    print("Reindex complete!")
    print("=" * 80)
    print(f"Added: {summary.added}")
    print(f"Updated: {summary.updated}")
    print(f"Deleted: {summary.deleted}")
    print(f"Unchanged: {summary.unchanged}")
    print(f"Total chunks: {summary.total_chunks}")
    print(f"API calls: {summary.api_call_count}")


if __name__ == "__main__":
    reindex_testdocs()
