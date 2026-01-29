"""Search API request and response schemas."""

from pydantic import BaseModel, Field
from typing import List, Optional


class SearchRequest(BaseModel):
    """検索リクエスト"""
    query: str = Field(..., min_length=1, description="検索クエリ")
    top_k: Optional[int] = Field(5, ge=1, le=100, description="返却件数")


class SearchResultItem(BaseModel):
    """検索結果の個別アイテム"""
    file_path: str
    heading: str
    content: str
    score: float = Field(..., ge=0.0, le=1.0)
    chunk_index: int


class SearchResponse(BaseModel):
    """検索レスポンス"""
    results: List[SearchResultItem]
    total_chunks: int
    query: str
    execution_time_ms: float
