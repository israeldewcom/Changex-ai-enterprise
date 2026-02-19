from app import celery
import logging

logger = logging.getLogger(__name__)

@celery.task
def heartbeat():
    """Periodic task to check system health."""
    logger.info("Heartbeat: Celery worker is alive")
    return {'status': 'ok'}
