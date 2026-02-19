"""
Real-time communication via WebSockets.
"""
from app.extensions import socketio, celery
from flask_socketio import emit
import logging

logger = logging.getLogger(__name__)

@celery.task
def send_course_update(course_offering_id: int, event_type: str, data: dict):
    """
    Send a real-time update to all users in a course room.
    """
    room = f"course_{course_offering_id}"
    socketio.emit(event_type, data, room=room)
    logger.info(f"Real-time event {event_type} sent to room {room}")

@celery.task
def send_user_notification(user_id: int, notification: dict):
    """
    Send a real-time notification to a specific user.
    """
    room = f"user_{user_id}"
    socketio.emit('notification', notification, room=room)

def emit_notification(user_id: int, notification: dict):
    """Emit notification to user room (synchronous, for use within request)."""
    room = f"user_{user_id}"
    socketio.emit('notification', notification, room=room)
