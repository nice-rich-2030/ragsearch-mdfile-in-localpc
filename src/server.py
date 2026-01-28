"""MCP Server for local RAG search."""

import argparse
import logging
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from .config import load_config
from .db import FileDB, VectorStore
from .embedder import Embedder
from .searcher import Searcher
from .indexer import Indexer

# Load environment variables from .env file
load_dotenv()


# Global instances
app_config = None
file_db = None
vector_store = None
embedder = None
searcher = None
indexer = None
logger = None


@contextmanager
def timer(label: str):
    """
    Context manager for timing code blocks.
    
    Args:
        label: Label for the timed block
    """
    start = time.perf_counter()
    yield
    elapsed_ms = (time.perf_counter() - start) * 1000
    logger.debug(f"[TIMER] {label}: {elapsed_ms:.1f}ms")


def setup_logging(verbose: bool = False):
    """
    Setup logging configuration.

    Args:
        verbose: Enable DEBUG level logging
    """
    global logger

    level = logging.DEBUG if verbose else logging.INFO

    # Create handlers
    handlers = [
        logging.StreamHandler(sys.stderr),
        logging.FileHandler('rag_server.log', encoding='utf-8')
    ]

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized (verbose={verbose})")


def initialize_components(docs_dir: Path, data_dir: Path):
    """
    Initialize all components.
    
    Args:
        docs_dir: Documents directory
        data_dir: Data directory for persistence
    """
    global app_config, file_db, vector_store, embedder, searcher, indexer
    
    logger.info(f"Initializing RAG server for docs_dir: {docs_dir}")
    
    # Load configuration
    app_config = load_config(docs_dir=docs_dir)
    logger.debug("Configuration loaded")
    
    # Initialize database
    db_path = data_dir / "files.db"
    file_db = FileDB(db_path)
    logger.debug(f"FileDB initialized: {db_path}")
    
    # Initialize vector store
    chroma_dir = data_dir / "chroma"
    vector_store = VectorStore(chroma_dir, app_config.chromadb)
    logger.debug(f"VectorStore initialized: {chroma_dir}")
    
    # Initialize embedder
    embedder = Embedder(app_config.embedding, app_config.retry)
    logger.debug("Embedder initialized")
    
    # Initialize searcher
    searcher = Searcher(embedder, vector_store)
    logger.debug("Searcher initialized")
    
    # Initialize indexer
    indexer = Indexer(
        docs_dir,
        file_db,
        vector_store,
        embedder,
        app_config.scanner,
        app_config.chunker
    )
    logger.debug("Indexer initialized")
    
    logger.info("All components initialized successfully")


async def handle_search(query: str, top_k: int = None) -> Dict[str, Any]:
    """
    Handle search request.
    
    Args:
        query: Search query
        top_k: Number of results to return
        
    Returns:
        Search results dictionary
    """
    if top_k is None:
        top_k = app_config.search.default_top_k
    
    logger.info(f"Search request: query='{query}', top_k={top_k}")
    
    # Check if index is empty, auto-reindex if needed
    if vector_store.count() == 0:
        logger.info("Index is empty, performing initial indexing...")
        await handle_reindex()
    
    # Perform search with timing
    with timer("search_total"):
        with timer("query_embedding"):
            results = searcher.search(query, top_k)
        
        logger.debug(f"Search returned {len(results)} results")
        
        # Log results in debug mode
        for i, result in enumerate(results, 1):
            logger.debug(
                f"  [{i}] score={result.score:.2f} file={result.file_path} "
                f"heading=\"{result.heading}\""
            )
    
    # Format response
    return {
        "results": [
            {
                "file_path": r.file_path,
                "heading": r.heading,
                "content": r.content,
                "score": r.score,
                "chunk_index": r.chunk_index
            }
            for r in results
        ],
        "total_chunks": vector_store.count(),
        "query": query
    }


async def handle_reindex() -> Dict[str, Any]:
    """
    Handle reindex request.

    Returns:
        Reindex summary dictionary
    """
    logger.info("Reindex request received")

    with timer("reindex_total"):
        summary = indexer.update()

    # Format response
    return {
        "added": summary.added,
        "updated": summary.updated,
        "deleted": summary.deleted,
        "unchanged": summary.unchanged,
        "total_chunks": summary.total_chunks,
        "api_call_count": summary.api_call_count
    }


def create_server(docs_dir: Path, data_dir: Path) -> Server:
    """
    Create MCP server instance.
    
    Args:
        docs_dir: Documents directory
        data_dir: Data directory
        
    Returns:
        MCP Server instance
    """
    server = Server("local-rag")
    
    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        """List available tools."""
        return [
            types.Tool(
                name="search",
                description="Search local documents using semantic search",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "top_k": {
                            "type": "integer",
                            "description": "Number of results to return (default: 5)",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            ),
            types.Tool(
                name="reindex",
                description="Rebuild document index (differential update)",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        """Handle tool calls."""
        try:
            if name == "search":
                query = arguments.get("query")
                top_k = arguments.get("top_k")
                
                if not query:
                    raise ValueError("query parameter is required")
                
                result = await handle_search(query, top_k)
                
                # Format results as text
                text_parts = [f"Found {len(result['results'])} results for query: '{query}'\n"]
                text_parts.append(f"Total chunks in index: {result['total_chunks']}\n\n")
                
                for i, r in enumerate(result['results'], 1):
                    text_parts.append(f"--- Result {i} (score: {r['score']:.3f}) ---\n")
                    text_parts.append(f"File: {r['file_path']}\n")
                    if r['heading']:
                        text_parts.append(f"Heading: {r['heading']}\n")
                    text_parts.append(f"\n{r['content']}\n\n")
                
                return [types.TextContent(
                    type="text",
                    text="".join(text_parts)
                )]
            
            elif name == "reindex":
                result = await handle_reindex()

                text = (
                    f"Index update complete:\n"
                    f"  Added: {result['added']}\n"
                    f"  Updated: {result['updated']}\n"
                    f"  Deleted: {result['deleted']}\n"
                    f"  Unchanged: {result['unchanged']}\n"
                    f"  Total chunks: {result['total_chunks']}\n"
                    f"  API calls: {result['api_call_count']}\n"
                )

                return [types.TextContent(
                    type="text",
                    text=text
                )]
            
            else:
                raise ValueError(f"Unknown tool: {name}")
        
        except Exception as e:
            logger.error(f"Tool call failed: {e}", exc_info=True)
            return [types.TextContent(
                type="text",
                text=f"Error: {str(e)}"
            )]
    
    return server


async def main_async(args):
    """Async main function."""
    # Setup logging
    setup_logging(args.verbose)
    
    # Resolve paths
    docs_dir = Path(args.docs_dir).resolve()
    
    if args.data_dir:
        data_dir = Path(args.data_dir).resolve()
    else:
        data_dir = docs_dir / ".rag-index"
    
    # Validate docs_dir
    if not docs_dir.exists():
        logger.error(f"Documents directory does not exist: {docs_dir}")
        sys.exit(1)
    
    # Initialize components
    initialize_components(docs_dir, data_dir)
    
    # Create and run server
    server = create_server(docs_dir, data_dir)
    
    logger.info("Starting MCP server...")
    
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Local RAG MCP Server"
    )
    parser.add_argument(
        "--docs-dir",
        required=True,
        help="Documents directory to index and search"
    )
    parser.add_argument(
        "--data-dir",
        help="Data directory for persistence (default: <docs-dir>/.rag-index)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging"
    )
    
    args = parser.parse_args()
    
    import asyncio
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
