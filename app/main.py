from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import settings
from app.core.logging import RequestLoggingMiddleware, logger, setup_logging
from app.database.database import initialize_desktop_database, wait_for_database
from app.routers.auth import router as auth_router
from app.routers.chat import router as chat_router
from app.routers.conversations import router as conversations_router
from app.routers.desktop import router as desktop_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router
from app.routers.memories import router as memories_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings.validate_for_startup()
    logger.info(
        "Starting %s version=%s env=%s",
        settings.APP_NAME,
        settings.APP_VERSION,
        settings.APP_ENV,
    )
    initialize_desktop_database()
    wait_for_database()
    try:
        yield
    finally:
        logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="An AI-powered personal knowledge management system",
    lifespan=lifespan,
    docs_url="/docs" if settings.API_DOCS_ENABLED else None,
    redoc_url="/redoc" if settings.API_DOCS_ENABLED else None,
    openapi_url="/openapi.json" if settings.API_DOCS_ENABLED else None,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)
if settings.TRUSTED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.TRUSTED_HOSTS,
    )


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(
        "Unhandled application exception request_id=%s path=%s",
        request.headers.get("x-request-id", "-"),
        request.url.path,
    )
    detail = str(exc) if settings.DEBUG and not settings.is_production else (
        "Internal server error"
    )
    return JSONResponse(status_code=500, content={"detail": detail})


if not settings.DESKTOP_MODE:
    @app.get("/")
    def home():
        return {
            "message": "Personal AI Assistant API is running"
        }


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversations_router)
app.include_router(documents_router)
app.include_router(memories_router)

if settings.DESKTOP_MODE:
    app.include_router(health_router, prefix="/api")
    app.include_router(auth_router, prefix="/api")
    app.include_router(chat_router, prefix="/api")
    app.include_router(conversations_router, prefix="/api")
    app.include_router(documents_router, prefix="/api")
    app.include_router(memories_router, prefix="/api")
    app.include_router(desktop_router, prefix="/api")
    _frontend_dir = Path(settings.DESKTOP_FRONTEND_DIR)
    _index_file = _frontend_dir / "index.html"
    if not _index_file.exists():
        raise RuntimeError(
            "Desktop frontend bundle is missing. Run npm.cmd run build in frontend."
        )
    _assets_dir = _frontend_dir / "assets"
    if _assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def desktop_frontend(path: str):
        requested = (_frontend_dir / path).resolve()
        if (
            requested.is_file()
            and _frontend_dir.resolve() in requested.parents
            and requested.name != ".env"
        ):
            return FileResponse(requested)
        return FileResponse(_index_file)
