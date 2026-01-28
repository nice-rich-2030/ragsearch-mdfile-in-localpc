"""Tests for chunker module."""

import pytest
from pathlib import Path
from src.chunker import chunk_file, chunk_markdown, chunk_text, Chunk
from src.config import ChunkerConfig


@pytest.fixture
def config():
    """Default chunker configuration."""
    return ChunkerConfig()


def test_chunk_markdown_with_headings(config):
    """Test Markdown chunking with headings."""
    content = """# Heading 1

This is the first section.

## Heading 2

This is the second section.

### Heading 3

This is the third section.
"""
    
    chunks = chunk_markdown(content, config)
    
    assert len(chunks) >= 3
    assert any("# Heading 1" in chunk.content for chunk in chunks)
    assert any("## Heading 2" in chunk.content for chunk in chunks)


def test_chunk_markdown_with_preamble(config):
    """Test Markdown chunking with preamble."""
    content = """This is preamble text before any heading.

# First Heading

This is content under the heading.
"""
    
    chunks = chunk_markdown(content, config)
    
    assert len(chunks) >= 2
    # First chunk should be preamble
    assert "preamble" in chunks[0].content.lower()


def test_chunk_text_paragraphs(config):
    """Test text chunking by paragraphs."""
    content = """First paragraph.

Second paragraph.

Third paragraph.
"""
    
    chunks = chunk_text(content, config)
    
    assert len(chunks) == 3
    assert "First paragraph" in chunks[0].content
    assert "Second paragraph" in chunks[1].content
    assert "Third paragraph" in chunks[2].content


def test_chunk_oversized_splitting(config):
    """Test oversized chunk splitting."""
    # Create a very long paragraph
    long_text = "This is a sentence. " * 200  # > 3000 chars
    
    chunks = chunk_text(long_text, config)
    
    # Should be split into multiple chunks
    assert len(chunks) > 1
    
    # Each chunk should be <= max_chunk_chars
    for chunk in chunks:
        assert len(chunk.content) <= config.max_chunk_chars


def test_chunk_file_md(config):
    """Test chunk_file with .md extension."""
    content = "# Test\n\nContent here."
    path = Path("test.md")
    
    chunks = chunk_file(path, content, config)
    
    assert len(chunks) >= 1
    assert chunks[0].chunk_index == 0


def test_chunk_file_txt(config):
    """Test chunk_file with .txt extension."""
    content = "Paragraph 1.\n\nParagraph 2."
    path = Path("test.txt")
    
    chunks = chunk_file(path, content, config)
    
    assert len(chunks) >= 1


def test_min_chunk_size_filter(config):
    """Test that small chunks are filtered out."""
    content = "# Big Heading\n\nLarge content here.\n\n## Small\n\nX"
    
    chunks = chunk_markdown(content, config)
    
    # Very small chunks should be filtered
    for chunk in chunks:
        assert len(chunk.content.strip()) >= config.min_chunk_chars
