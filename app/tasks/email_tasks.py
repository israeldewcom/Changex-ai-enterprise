from app import celery
from app.utils.email import send_email

@celery.task
def send_async_email(recipient, subject, body_html=None, body_text=None, template=None, context=None):
    send_email(recipient, subject, template, context, body_html, body_text)
