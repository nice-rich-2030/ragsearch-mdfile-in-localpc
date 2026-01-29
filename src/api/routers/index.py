"""Index management API router."""

from fastapi import APIRouter, Request, HTTPException
from ..schemas.index import IndexRebuildRequest, IndexRebuildResponse, IndexStatusResponse
import time

router = APIRouter()


@router.post("/index/rebuild", response_model=IndexRebuildResponse)
async def rebuild_index(request: IndexRebuildRequest, app_request: Request):
    """インデックス再構築"""
    app_state = app_request.app.state.app_state

    start_time = time.perf_counter()

    try:
        summary = app_state.indexer.update()
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return IndexRebuildResponse(
            added=summary.added,
            updated=summary.updated,
            deleted=summary.deleted,
            unchanged=summary.unchanged,
            total_chunks=summary.total_chunks,
            api_call_count=summary.api_call_count,
            execution_time_ms=elapsed_ms
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/index/status", response_model=IndexStatusResponse)
async def index_status(app_request: Request):
    """インデックス状態取得"""
    app_state = app_request.app.state.app_state

    try:
        total_files = len(app_state.file_db.get_all_files())

        return IndexStatusResponse(
            total_chunks=app_state.vector_store.count(),
            total_files=total_files
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
