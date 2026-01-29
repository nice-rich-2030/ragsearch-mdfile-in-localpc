"""Debug chunker - Show how a file is split into chunks."""

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

load_dotenv()

from src.shared.config import load_config
from src.shared.chunker import chunk_file


def debug_chunker(file_path: Path, docs_dir: Path):
    """ファイルのチャンク分割をデバッグ表示"""

    print("=" * 80)
    print("Chunker Debug Tool")
    print("=" * 80)
    print(f"File: {file_path}")
    print()

    # 設定読み込み
    app_config = load_config(docs_dir=docs_dir)
    print(f"Chunker config:")
    print(f"  max_chunk_chars: {app_config.chunker.max_chunk_chars}")
    print(f"  min_chunk_chars: {app_config.chunker.min_chunk_chars}")
    print(f"  heading_levels: {app_config.chunker.heading_levels}")
    print()

    # ファイル読み込み
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"File content ({len(content)} chars):")
    print("-" * 80)
    # Show first 500 chars with line numbers
    lines = content.split('\n')
    for i, line in enumerate(lines[:20], 1):
        print(f"{i:3d}: {line}")
    if len(lines) > 20:
        print(f"... ({len(lines) - 20} more lines)")
    print("-" * 80)
    print()

    # チャンク分割実行
    chunks = chunk_file(file_path, content, app_config.chunker)

    print(f"Generated {len(chunks)} chunks:")
    print("=" * 80)

    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i} (index={chunk.chunk_index}):")
        print(f"  Heading: {chunk.heading if chunk.heading else '(no heading)'}")
        print(f"  Length: {len(chunk.content)} chars")
        print(f"  Content preview (first 500 chars):")
        if len(chunk.content) <= 500:
            print(f"    {chunk.content}")
        else:
            print(f"    {chunk.content[:500]}...")

        # Check for target text
        target_text = "Pythonでのエラーハンドリングは、プログラムの堅牢性を高める重要な要素です"
        if target_text in chunk.content:
            print(f"  [FOUND] Target text is in this chunk!")

    print()
    print("=" * 80)
    print("Summary:")
    print(f"  Total chunks: {len(chunks)}")
    print(f"  Total indexed chars: {sum(len(c.content) for c in chunks)}")
    print(f"  Original file chars: {len(content)}")
    print(f"  Coverage: {sum(len(c.content) for c in chunks) / len(content) * 100:.1f}%")


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_chunker.py <file_path> [docs_dir]")
        print("\nExample:")
        print("  python debug_chunker.py ./test-docs/error-handling.md")
        print("  python debug_chunker.py ./test-docs/error-handling.md ./test-docs")
        sys.exit(1)

    file_path = Path(sys.argv[1]).resolve()
    docs_dir = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else file_path.parent

    if not file_path.exists():
        print(f"[ERROR] File does not exist: {file_path}")
        sys.exit(1)

    debug_chunker(file_path, docs_dir)


if __name__ == "__main__":
    main()
