"""
SMS sending with Twilio.
"""
from twilio.rest import Client
from flask import current_app
import logging

logger = logging.getLogger(__name__)

def send_sms(to_number: str, body: str):
    """Send an SMS via Twilio."""
    account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
    auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
    from_number = current_app.config.get('TWILIO_PHONE_NUMBER')
    
    if not all([account_sid, auth_token, from_number]):
        logger.error("Twilio credentials not configured")
        return False
    
    client = Client(account_sid, auth_token)
    try:
        message = client.messages.create(
            body=body,
            from_=from_number,
            to=to_number
        )
        logger.info(f"SMS sent to {to_number}, SID: {message.sid}")
        return True
    except Exception as e:
        logger.error(f"Failed to send SMS to {to_number}: {e}")
        return False
