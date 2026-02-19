"""
Celery tasks package – imports all task modules to ensure they are registered.
"""
from .email_tasks import send_async_email
from .model_training import train_model
from .report_tasks import generate_institution_report
from .monitoring import heartbeat

# Import the modules so Celery discovers the tasks
from . import email_tasks, model_training, report_tasks, monitoring

__all__ = [
    'send_async_email',
    'train_model',
    'generate_institution_report',
    'heartbeat',
]
