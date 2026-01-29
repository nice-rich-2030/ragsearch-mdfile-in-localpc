"""FastAPI application for Local RAG."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import search, index
from .dependencies import get_app_state
from .middleware import timing_middleware
import logging

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# FastAPIアプリケーション作成
app = FastAPI(
    title="Local RAG API",
    description="Semantic search API for local documents using Gemini Embedding and ChromaDB",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では制限すべき
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# タイミング計測ミドルウェア
app.middleware("http")(timing_middleware)

# アプリケーション状態初期化（起動時1回のみ）
app.state.app_state = get_app_state()

# ルーター登録
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(index.router, prefix="/api/v1", tags=["index"])


# ヘルスチェック
@app.get("/health")
async def health():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "index_size": app.state.app_state.vector_store.count()
    }
