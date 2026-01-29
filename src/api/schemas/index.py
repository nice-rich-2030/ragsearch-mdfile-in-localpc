"""Index API request and response schemas."""

from pydantic import BaseModel


class IndexRebuildRequest(BaseModel):
    """インデックス再構築リクエスト"""
    pass  # 将来的に force_full_rebuild などを追加可能


class IndexRebuildResponse(BaseModel):
    """インデックス再構築レスポンス"""
    added: int
    updated: int
    deleted: int
    unchanged: int
    total_chunks: int
    api_call_count: int
    execution_time_ms: float


class IndexStatusResponse(BaseModel):
    """インデックス状態レスポンス"""
    total_chunks: int
    total_files: int
