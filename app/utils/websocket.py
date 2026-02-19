"""
WebSocket event handlers for real-time notifications.
"""
from flask_socketio import emit, join_room, leave_room
from flask import request, g
from app.extensions import socketio
from app.auth import jwt_required
import logging

logger = logging.getLogger(__name__)

@socketio.on('connect')
def handle_connect():
    """Client connects to WebSocket."""
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('authenticate')
@jwt_required  # Note: need to adapt JWT for WebSocket
def handle_authenticate(data):
    """Authenticate socket connection and join user rooms."""
    user_id = g.current_user.id
    join_room(f"user_{user_id}")
    emit('authenticated', {'msg': 'Authenticated'})

@socketio.on('join_course')
def handle_join_course(data):
    """Join a course room for real-time updates."""
    course_offering_id = data.get('course_offering_id')
    if course_offering_id:
        join_room(f"course_{course_offering_id}")
        emit('joined', {'room': f"course_{course_offering_id}"})

@socketio.on('leave_course')
def handle_leave_course(data):
    course_offering_id = data.get('course_offering_id')
    if course_offering_id:
        leave_room(f"course_{course_offering_id}")
        emit('left', {'room': f"course_{course_offering_id}"})
