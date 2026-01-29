"""Text chunking module for document processing."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List

from .config import ChunkerConfig


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    content: str
    chunk_index: int
    heading: str = ""


def chunk_file(path: Path, content: str, config: ChunkerConfig) -> List[Chunk]:
    """
    Split file content into chunks based on file extension.
    
    Args:
        path: File path (used to determine extension)
        content: File content
        config: Chunker configuration
        
    Returns:
        List of Chunk objects
    """
    suffix = path.suffix.lower()
    
    if suffix == '.md':
        return chunk_markdown(content, config)
    elif suffix == '.txt':
        return chunk_text(content, config)
    else:
        # Fallback to text chunking
        return chunk_text(content, config)


def chunk_markdown(content: str, config: ChunkerConfig) -> List[Chunk]:
    """
    Split Markdown content by headings.
    
    Args:
        content: Markdown content
        config: Chunker configuration
        
    Returns:
        List of Chunk objects
    """
    chunks = []
    
    # Build regex pattern for heading levels
    max_level = max(config.heading_levels)
    heading_pattern = re.compile(r'^(#{1,' + str(max_level) + r'})\s+(.+)$', re.MULTILINE)
    
    # Find all heading positions
    headings = []
    for match in heading_pattern.finditer(content):
        level = len(match.group(1))
        if level in config.heading_levels:
            headings.append({
                'pos': match.start(),
                'level': level,
                'text': match.group(0)
            })
    
    # Split content by headings
    sections = []
    
    # Handle content before first heading
    if headings:
        if headings[0]['pos'] > 0:
            preamble = content[:headings[0]['pos']].strip()
            if preamble:
                sections.append({
                    'heading': '',
                    'content': preamble
                })
        
        # Split between headings
        for i, heading in enumerate(headings):
            end_pos = headings[i + 1]['pos'] if i + 1 < len(headings) else len(content)
            section_content = content[heading['pos']:end_pos].strip()
            
            if section_content:
                sections.append({
                    'heading': heading['text'],
                    'content': section_content
                })
    else:
        # No headings found, treat entire content as one section
        if content.strip():
            sections.append({
                'heading': '',
                'content': content.strip()
            })
    
    # Process sections and handle oversized chunks
    chunk_index = 0
    for section in sections:
        section_chunks = _split_oversized(
            section['content'], 
            config.max_chunk_chars
        )
        
        for chunk_content in section_chunks:
            # Skip chunks that are too small
            if len(chunk_content.strip()) < config.min_chunk_chars:
                continue
            
            chunks.append(Chunk(
                content=chunk_content.strip(),
                chunk_index=chunk_index,
                heading=section['heading']
            ))
            chunk_index += 1
    
    return chunks


def chunk_text(content: str, config: ChunkerConfig) -> List[Chunk]:
    """
    Split plain text content by paragraphs (double newlines).
    
    Args:
        content: Text content
        config: Chunker configuration
        
    Returns:
        List of Chunk objects
    """
    chunks = []
    
    # Split by double newlines (paragraphs)
    paragraphs = re.split(r'\n\n+', content)
    
    chunk_index = 0
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # Handle oversized paragraphs
        para_chunks = _split_oversized(para, config.max_chunk_chars)
        
        for chunk_content in para_chunks:
            # Skip chunks that are too small
            if len(chunk_content.strip()) < config.min_chunk_chars:
                continue
            
            chunks.append(Chunk(
                content=chunk_content.strip(),
                chunk_index=chunk_index,
                heading=""
            ))
            chunk_index += 1
    
    return chunks


def _split_oversized(text: str, max_chars: int) -> List[str]:
    """
    Split oversized text at sentence boundaries.
    
    Args:
        text: Text to split
        max_chars: Maximum characters per chunk
        
    Returns:
        List of text chunks
    """
    if len(text) <= max_chars:
        return [text]
    
    chunks = []
    remaining = text
    
    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break
        
        # Try to find sentence boundary within max_chars
        chunk = remaining[:max_chars]
        
        # Look for sentence boundaries (。, ., \n\n)
        boundaries = []
        for delimiter in ['。', '.', '\n\n', '\n']:
            pos = chunk.rfind(delimiter)
            if pos != -1:
                boundaries.append(pos + len(delimiter))
        
        if boundaries:
            # Split at the last boundary found
            split_pos = max(boundaries)
            chunks.append(remaining[:split_pos])
            remaining = remaining[split_pos:].lstrip()
        else:
            # No boundary found, force split at max_chars
            chunks.append(remaining[:max_chars])
            remaining = remaining[max_chars:]
    
    return chunks
