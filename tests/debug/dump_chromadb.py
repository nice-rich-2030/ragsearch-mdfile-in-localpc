"""ChromaDB dump tool - Display all indexed documents."""

import sys
from pathlib import Path
from dotenv import load_dotenv

# Add project root to sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Windows console encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# .envファイル読み込み
load_dotenv()

# src.shared モジュールをインポート
from src.shared.config import load_config
from src.shared.db import VectorStore


def dump_chromadb(docs_dir: Path, data_dir: Path = None):
    """ChromaDBの内容をダンプする"""

    # データディレクトリの決定
    if data_dir is None:
        data_dir = docs_dir / ".rag-index"

    print("=" * 80)
    print("ChromaDB Dump Tool")
    print("=" * 80)
    print(f"Documents directory: {docs_dir}")
    print(f"Data directory: {data_dir}")
    print()

    # 設定読み込み
    try:
        app_config = load_config(docs_dir=docs_dir)
        print("[OK] Configuration loaded")
    except Exception as e:
        print(f"[ERROR] Failed to load configuration: {e}")
        return

    # VectorStore初期化
    try:
        chroma_dir = data_dir / "chroma"
        vector_store = VectorStore(chroma_dir, app_config.chromadb)
        print(f"[OK] VectorStore initialized: {chroma_dir}")
    except Exception as e:
        print(f"[ERROR] Failed to initialize VectorStore: {e}")
        return

    # 総チャンク数取得
    total_count = vector_store.count()
    print(f"[OK] Total chunks in index: {total_count}")
    print()

    if total_count == 0:
        print("[WARNING] Index is empty. Please run reindex first.")
        return

    print("=" * 80)
    print("Fetching all documents...")
    print("=" * 80)

    try:
        # ChromaDBから全ドキュメントを取得
        collection = vector_store.collection

        # すべてのドキュメントを取得（limit=Noneで全件取得）
        results = collection.get(
            include=["documents", "metadatas", "embeddings"]
        )

        ids = results.get("ids", [])
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        embeddings = results.get("embeddings", [])

        print(f"Retrieved {len(documents)} chunks")
        print()

        # ファイルごとにグループ化
        file_groups = {}
        for i, (doc_id, doc, meta, emb) in enumerate(zip(ids, documents, metadatas, embeddings)):
            file_path = meta.get("file_path", "unknown")
            if file_path not in file_groups:
                file_groups[file_path] = []
            file_groups[file_path].append({
                "id": doc_id,
                "content": doc,
                "metadata": meta,
                "embedding_dim": len(emb) if emb else 0
            })

        # ファイルごとに表示
        for file_path in sorted(file_groups.keys()):
            chunks = file_groups[file_path]
            print("=" * 80)
            print(f"File: {file_path}")
            print(f"Chunks: {len(chunks)}")
            print("=" * 80)

            for idx, chunk in enumerate(chunks, 1):
                print(f"\n--- Chunk {idx}/{len(chunks)} ---")
                print(f"ID: {chunk['id']}")
                print(f"Embedding dimension: {chunk['embedding_dim']}")

                # メタデータ表示
                meta = chunk['metadata']
                print(f"Metadata:")
                print(f"  - file_path: {meta.get('file_path', 'N/A')}")
                print(f"  - chunk_index: {meta.get('chunk_index', 'N/A')}")
                print(f"  - heading: {meta.get('heading', 'N/A')}")

                # 内容表示（最初の200文字）
                content = chunk['content']
                print(f"Content ({len(content)} chars):")
                if len(content) <= 200:
                    print(f"  {content}")
                else:
                    print(f"  {content[:200]}...")

                # ユーザーが検索したいテキストが含まれているかチェック
                search_text = "Pythonでのエラーハンドリングは、プログラムの堅牢性を高める重要な要素です"
                if search_text in content:
                    print(f"  [FOUND] Contains search text!")
                elif "エラーハンドリング" in content:
                    print(f"  [PARTIAL] Contains 'エラーハンドリング' but not exact match")

            print()

        # 統計情報
        print("=" * 80)
        print("Statistics")
        print("=" * 80)
        print(f"Total files: {len(file_groups)}")
        print(f"Total chunks: {len(documents)}")
        print(f"Average chunks per file: {len(documents) / len(file_groups):.1f}")

        # 各ファイルのチャンク数
        print("\nChunks per file:")
        for file_path, chunks in sorted(file_groups.items(), key=lambda x: len(x[1]), reverse=True):
            print(f"  {file_path}: {len(chunks)} chunks")

    except Exception as e:
        print(f"[ERROR] Failed to fetch documents: {e}")
        import traceback
        traceback.print_exc()


def main():
    """メイン関数"""
    if len(sys.argv) < 2:
        print("Usage: python dump_chromadb.py <docs_dir> [data_dir]")
        print("\nExample:")
        print("  python dump_chromadb.py ./test-docs")
        print("  python dump_chromadb.py ./test-docs ./data")
        sys.exit(1)

    docs_dir = Path(sys.argv[1]).resolve()
    data_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else None

    if not docs_dir.exists():
        print(f"[ERROR] Documents directory does not exist: {docs_dir}")
        sys.exit(1)

    dump_chromadb(docs_dir, data_dir)


if __name__ == "__main__":
    main()
