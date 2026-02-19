from flask import Blueprint, request, jsonify, g
from app.auth import jwt_required
from app.extensions import socketio
from app.utils.websocket import emit_notification

bp = Blueprint('realtime', __name__)

@bp.route('/notify', methods=['POST'])
@jwt_required
def send_notification():
    """Send a real-time notification to a specific user (for testing)."""
    data = request.get_json()
    user_id = data.get('user_id')
    message = data.get('message')
    if not user_id or not message:
        return jsonify({'msg': 'user_id and message required'}), 400
    emit_notification(user_id, {'message': message, 'from': g.current_user.id})
    return jsonify({'msg': 'Notification sent'})
