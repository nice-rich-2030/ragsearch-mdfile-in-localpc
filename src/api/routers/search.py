"""Search API router."""

from fastapi import APIRouter, Request, HTTPException
from ..schemas.search import SearchRequest, SearchResponse, SearchResultItem
import time

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest, app_request: Request):
    """セマンティック検索"""
    app_state = app_request.app.state.app_state

    start_time = time.perf_counter()

    try:
        # インデックスが空なら自動構築
        if app_state.vector_store.count() == 0:
            app_state.indexer.update()

        # 検索実行
        results = app_state.searcher.search(request.query, request.top_k)

        # レスポンス構築
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return SearchResponse(
            results=[
                SearchResultItem(
                    file_path=r.file_path,
                    heading=r.heading,
                    content=r.content,
                    score=r.score,
                    chunk_index=r.chunk_index
                )
                for r in results
            ],
            total_chunks=app_state.vector_store.count(),
            query=request.query,
            execution_time_ms=elapsed_ms
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
