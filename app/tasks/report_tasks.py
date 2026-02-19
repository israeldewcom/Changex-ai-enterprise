from app import celery
from app.services.analytics import generate_report

@celery.task
def generate_institution_report(institution_id, report_type):
    # Placeholder
    pass
