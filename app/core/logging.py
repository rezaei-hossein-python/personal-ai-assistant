import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings


def setup_logging():
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    if settings.DESKTOP_LOG_DIR:
        log_path = Path(settings.DESKTOP_LOG_DIR) / "backend.log"
        handlers.append(
            RotatingFileHandler(
                str(log_path),
                maxBytes=1_000_000,
                backupCount=5,
                encoding="utf-8",
            )
        )
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=handlers,
        force=True,
    )
    logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))


logger = logging.getLogger("personal-ai-assistant")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(
                "Unhandled request exception request_id=%s method=%s path=%s "
                "duration_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "Request completed request_id=%s method=%s path=%s status=%s "
            "duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response
