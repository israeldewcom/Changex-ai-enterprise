"""
Notification service for in-app, email, SMS, and real-time.
"""
from app import celery
from app.models import Notification, User
from app.extensions import db
from app.utils.email import send_async_email
from app.utils.sms import send_sms
from app.utils.websocket import emit_notification
import logging

logger = logging.getLogger(__name__)

@celery.task
def notify_user(user_id: int, notification_type: str, data: dict):
    """
    Create a notification and send via user's preferred channels.
    """
    user = User.query.get(user_id)
    if not user:
        logger.warning(f"User {user_id} not found for notification")
        return

    # Create in-app notification
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        data=data,
        title=data.get('title', 'Notification'),
        message=data.get('message', '')
    )
    db.session.add(notification)
    db.session.commit()
    
    # Emit real-time if user connected
    emit_notification(user_id, notification.to_dict())
    
    # Send email if user has email notifications enabled
    if user.profile.get('email_notifications', True):
        send_async_email.delay(
            user.email,
            data.get('title', 'ChangeX Notification'),
            body_html=data.get('html', ''),
            body_text=data.get('text', '')
        )

    # Send SMS if enabled and phone number exists
    if user.profile.get('sms_notifications', False) and user.profile.get('phone'):
        send_sms(user.profile['phone'], data.get('text', ''))
    
    logger.info(f"Notification {notification_type} sent to user {user_id}")

@celery.task
def notify_course(course_offering_id: int, notification_type: str, data: dict, exclude_user_ids: list = None):
    """
    Send notification to all enrolled students in a course.
    """
    from app.models import Enrollment
    enrollments = Enrollment.query.filter_by(
        course_offering_id=course_offering_id,
        status='enrolled'
    ).all()
    exclude = set(exclude_user_ids or [])
    for e in enrollments:
        if e.user_id not in exclude:
            notify_user.delay(e.user_id, notification_type, data)
