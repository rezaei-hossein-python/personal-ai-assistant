from app.core.logging import logger


def get_system_status():
    logger.info("Generating system status")

    return {
        "application": "Personal AI Assistant",
        "status": "healthy"
    }
