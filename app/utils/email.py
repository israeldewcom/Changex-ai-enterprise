"""
Email sending with SendGrid.
"""
from flask_mail import Message
from app.extensions import mail, celery
from flask import current_app, render_template
import logging

logger = logging.getLogger(__name__)

def send_email(recipient: str, subject: str, template: str = None, 
               context: dict = None, body_html: str = None, body_text: str = None):
    """
    Send an email. Either provide template name with context, or raw html/text.
    """
    if template:
        body_html = render_template(f'emails/{template}.html', **(context or {}))
        body_text = render_template(f'emails/{template}.txt', **(context or {}))
    
    msg = Message(
        subject=subject,
        recipients=[recipient],
        html=body_html,
        body=body_text
    )
    try:
        mail.send(msg)
        logger.info(f"Email sent to {recipient}")
    except Exception as e:
        logger.error(f"Failed to send email to {recipient}: {e}")
        raise

@celery.task
def send_async_email(recipient: str, subject: str, template: str = None,
                     context: dict = None, body_html: str = None, body_text: str = None):
    """Send email asynchronously."""
    with current_app.app_context():
        send_email(recipient, subject, template, context, body_html, body_text)
