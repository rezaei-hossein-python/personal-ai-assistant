from app.core.logging import logger
from app.database.database import check_database_connection


def get_system_status():
    return {
        "application": "Personal AI Assistant",
        "status": "healthy",
    }


def get_readiness_status():
    logger.info("Checking readiness")
    check_database_connection()
    return {
        "application": "Personal AI Assistant",
        "status": "ready",
        "checks": {
            "database": "ok",
        },
    }
