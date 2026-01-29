"""Verbose debug chunker - Show detailed chunk processing."""

import sys
import re
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


def debug_chunk_markdown_verbose(content: str, config):
    """Markdownチャンク分割の詳細デバッグ"""

    print("=" * 80)
    print("VERBOSE Markdown Chunking Debug")
    print("=" * 80)
    print(f"Config:")
    print(f"  heading_levels: {config.heading_levels}")
    print(f"  min_chunk_chars: {config.min_chunk_chars}")
    print(f"  max_chunk_chars: {config.max_chunk_chars}")
    print()

    # Build regex pattern
    max_level = max(config.heading_levels)
    heading_pattern = re.compile(r'^(#{1,' + str(max_level) + r'})\s+(.+)$', re.MULTILINE)

    # Find all headings
    headings = []
    for match in heading_pattern.finditer(content):
        level = len(match.group(1))
        if level in config.heading_levels:
            headings.append({
                'pos': match.start(),
                'level': level,
                'text': match.group(0)
            })

    print(f"Found {len(headings)} headings:")
    for i, h in enumerate(headings):
        print(f"  {i}: pos={h['pos']}, level={h['level']}, text='{h['text']}'")
    print()

    # Split content by headings
    sections = []

    # Handle preamble
    if headings:
        if headings[0]['pos'] > 0:
            preamble = content[:headings[0]['pos']].strip()
            print(f"Preamble (before first heading):")
            print(f"  Length: {len(preamble)} chars")
            if preamble:
                print(f"  Content: {preamble[:100]}...")
                sections.append({
                    'heading': '',
                    'content': preamble
                })
                print(f"  [ADDED to sections]")
            else:
                print(f"  [EMPTY, skipped]")
            print()

        # Split between headings
        for i, heading in enumerate(headings):
            end_pos = headings[i + 1]['pos'] if i + 1 < len(headings) else len(content)
            section_content = content[heading['pos']:end_pos].strip()

            print(f"Section {i}: '{heading['text']}'")
            print(f"  Start pos: {heading['pos']}")
            print(f"  End pos: {end_pos}")
            print(f"  Raw length: {len(section_content)} chars")
            print(f"  Content preview: {section_content[:100]}...")

            if section_content:
                sections.append({
                    'heading': heading['text'],
                    'content': section_content
                })
                print(f"  [ADDED to sections]")
            else:
                print(f"  [EMPTY, skipped]")
            print()

    print(f"Total sections created: {len(sections)}")
    print()

    # Process sections
    print("=" * 80)
    print("Processing sections into chunks:")
    print("=" * 80)

    chunk_index = 0
    final_chunks = []

    for i, section in enumerate(sections):
        print(f"\nSection {i}: heading='{section['heading']}'")
        print(f"  Content length: {len(section['content'])} chars")

        # Check min_chunk_chars
        if len(section['content'].strip()) < config.min_chunk_chars:
            print(f"  [SKIP] Too small ({len(section['content'])} < {config.min_chunk_chars})")
            continue

        print(f"  [PASS] Size check OK")
        final_chunks.append({
            'heading': section['heading'],
            'content': section['content'],
            'chunk_index': chunk_index
        })
        chunk_index += 1

    print()
    print("=" * 80)
    print(f"Final result: {len(final_chunks)} chunks")
    print("=" * 80)

    return final_chunks


def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_chunker_verbose.py <file_path>")
        sys.exit(1)

    file_path = Path(sys.argv[1]).resolve()
    docs_dir = file_path.parent

    if not file_path.exists():
        print(f"[ERROR] File does not exist: {file_path}")
        sys.exit(1)

    # Load config
    app_config = load_config(docs_dir=docs_dir)

    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"File: {file_path}")
    print(f"Content length: {len(content)} chars")
    print()

    # Debug
    chunks = debug_chunk_markdown_verbose(content, app_config.chunker)

    print("\nFinal chunks:")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i}:")
        print(f"  Heading: {chunk['heading']}")
        print(f"  Content ({len(chunk['content'])} chars): {chunk['content'][:150]}...")


if __name__ == "__main__":
    main()
