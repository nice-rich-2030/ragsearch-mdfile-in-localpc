"""FastAPI middleware."""

from fastapi import Request
import time
import logging

logger = logging.getLogger(__name__)


async def timing_middleware(request: Request, call_next):
    """リクエスト処理時間を計測"""
    start_time = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start_time) * 1000

    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {elapsed_ms:.1f}ms")
    response.headers["X-Process-Time"] = f"{elapsed_ms:.1f}ms"

    return response
