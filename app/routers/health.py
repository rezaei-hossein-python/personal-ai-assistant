from fastapi import APIRouter, HTTPException, status

from app.core.logging import logger
from app.services.system_service import get_readiness_status, get_system_status


router = APIRouter()


@router.get("/health")
def health_check():
    return get_system_status()


@router.get("/ready")
def readiness_check():
    try:
        return get_readiness_status()
    except RuntimeError:
        logger.exception("Readiness check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Application is not ready",
        )
