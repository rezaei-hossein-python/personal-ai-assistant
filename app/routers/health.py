from fastapi import APIRouter

from app.core.logging import logger
from app.services.system_service import get_system_status


router = APIRouter()


@router.get("/health")
def health_check():
    logger.info("Health check requested")

    return get_system_status()