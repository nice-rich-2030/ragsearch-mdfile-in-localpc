"""Dependency injection for FastAPI."""

import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

from ..shared.config import load_config
from ..shared.db import FileDB, VectorStore
from ..shared.embedder import Embedder
from ..shared.searcher import Searcher
from ..shared.indexer import Indexer

load_dotenv()


@dataclass
class AppState:
    """アプリケーション状態（シングルトン）"""
    docs_dir: Path
    file_db: FileDB
    vector_store: VectorStore
    embedder: Embedder
    searcher: Searcher
    indexer: Indexer


def get_app_state() -> AppState:
    """環境変数からアプリケーション状態を初期化（起動時1回）"""
    docs_dir_str = os.getenv("DOCS_DIR")
    if not docs_dir_str:
        raise ValueError("DOCS_DIR environment variable must be set")

    docs_dir = Path(docs_dir_str).resolve()

    data_dir_str = os.getenv("DATA_DIR")
    if data_dir_str:
        data_dir = Path(data_dir_str).resolve()
    else:
        data_dir = docs_dir / ".rag-index"

    # 設定読込
    app_config = load_config(docs_dir=docs_dir)

    # DB初期化
    file_db = FileDB(data_dir / "files.db")
    vector_store = VectorStore(data_dir / "chroma", app_config.chromadb)

    # Embedder初期化
    embedder = Embedder(app_config.embedding, app_config.retry)

    # Searcher初期化
    searcher = Searcher(embedder, vector_store)

    # Indexer初期化
    indexer = Indexer(
        docs_dir, file_db, vector_store, embedder,
        app_config.scanner, app_config.chunker
    )

    return AppState(
        docs_dir=docs_dir,
        file_db=file_db,
        vector_store=vector_store,
        embedder=embedder,
        searcher=searcher,
        indexer=indexer
    )
