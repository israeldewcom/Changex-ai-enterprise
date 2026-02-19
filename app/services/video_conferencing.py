"""Video conferencing integration (Jitsi)."""
import secrets
from flask import current_app
from app.models import LiveSession, db


def create_jitsi_room(course_offering_id: int, title: str, start_time, end_time=None, created_by: int) -> LiveSession:
    """Create a Jitsi room and return LiveSession object."""
    # Generate unique room name
    room_name = f"{course_offering_id}-{secrets.token_urlsafe(8)}"
    base_url = current_app.config.get('JITSI_BASE_URL', 'https://meet.jit.si/')
    meeting_url = base_url + room_name

    session = LiveSession(
        course_offering_id=course_offering_id,
        title=title,
        start_time=start_time,
        end_time=end_time,
        meeting_url=meeting_url,
        created_by=created_by,
        status='scheduled'
    )
    db.session.add(session)
    db.session.commit()
    return session
