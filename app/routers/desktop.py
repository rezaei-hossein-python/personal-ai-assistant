from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status

from app.config import settings
from desktop.secrets import DesktopSecretService, SecretStorageError


router = APIRouter(prefix="/desktop", tags=["desktop"])


class DesktopStatusResponse(BaseModel):
    desktop_mode: bool
    app_version: str
    data_directory: str
    logs_directory: str
    database_backend: str
    backend_status: str
    openai_api_key_configured: bool


class SecretStatusResponse(BaseModel):
    configured: bool
    masked: str | None = None


class SaveOpenAIKeyRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=300)


class TestOpenAIKeyResponse(BaseModel):
    configured: bool
    valid: bool
    message: str


@router.get("/status", response_model=DesktopStatusResponse)
def desktop_status():
    _require_desktop_mode()
    return DesktopStatusResponse(
        desktop_mode=True,
        app_version=settings.APP_VERSION,
        data_directory=settings.DESKTOP_DATA_DIR,
        logs_directory=settings.DESKTOP_LOG_DIR,
        database_backend=settings.DATABASE_BACKEND,
        backend_status="ready",
        openai_api_key_configured=bool(settings.OPENAI_API_KEY),
    )


@router.get("/secrets/openai", response_model=SecretStatusResponse)
def openai_key_status():
    _require_desktop_mode()
    return SecretStatusResponse(
        configured=bool(settings.OPENAI_API_KEY),
        masked=_mask_secret(settings.OPENAI_API_KEY),
    )


@router.put("/secrets/openai", response_model=SecretStatusResponse)
def save_openai_key(request: SaveOpenAIKeyRequest):
    _require_desktop_mode()
    api_key = request.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="OpenAI API key is required")
    try:
        DesktopSecretService().set_secret("OPENAI_API_KEY", api_key)
    except SecretStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    settings.OPENAI_API_KEY = api_key
    return SecretStatusResponse(configured=True, masked=_mask_secret(api_key))


@router.delete("/secrets/openai", response_model=SecretStatusResponse)
def delete_openai_key():
    _require_desktop_mode()
    try:
        DesktopSecretService().delete_secret("OPENAI_API_KEY")
    except SecretStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    settings.OPENAI_API_KEY = ""
    return SecretStatusResponse(configured=False, masked=None)


@router.post("/secrets/openai/test", response_model=TestOpenAIKeyResponse)
def test_openai_key():
    _require_desktop_mode()
    if not settings.OPENAI_API_KEY:
        return TestOpenAIKeyResponse(
            configured=False,
            valid=False,
            message="OpenAI API key is not configured",
        )
    return TestOpenAIKeyResponse(
        configured=True,
        valid=True,
        message="OpenAI API key is configured",
    )


def _require_desktop_mode() -> None:
    if not settings.DESKTOP_MODE:
        raise HTTPException(status_code=404, detail="Not found")


def _mask_secret(secret: str) -> str | None:
    if not secret:
        return None
    if len(secret) <= 8:
        return "********"
    return f"{secret[:3]}...{secret[-4:]}"
