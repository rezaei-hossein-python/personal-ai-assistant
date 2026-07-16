from fastapi import APIRouter

from app.core.logging import logger


router = APIRouter()


@router.get("/health")
def health_check():
    logger.info("Health check requested")

    return {
        "status": "healthy",
        "service": "Personal AI Assistant"
    }