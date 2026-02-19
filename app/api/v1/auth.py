from flask import Blueprint, request, jsonify, g
from app import db
from app.models import User
from werkzeug.security import check_password_hash
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from app.utils.validators import UserRegistrationSchema, validate_password
from marshmallow import ValidationError
from app.auth import jwt_required as auth_jwt_required
from app.services.notification import notify_user
from app.utils.compliance import record_consent
from datetime import datetime

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['POST'])
def register():
    schema = UserRegistrationSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as e:
        return jsonify({'errors': e.messages}), 400

    if User.query.filter_by(email=data['email']).first():
        return jsonify({'msg': 'Email already exists'}), 400

    user = User(
        email=data['email'],
        full_name=data['full_name']
    )
    user.password = data['password']  # uses setter
    db.session.add(user)
    db.session.commit()

    # Record consent for terms
    record_consent(user.id, 'terms', True, request.remote_addr, request.user_agent.string)

    # Send welcome email
    notify_user.delay(user.id, 'welcome', {'name': user.full_name})

    return jsonify({'msg': 'User created', 'user': user.id}), 201

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data.get('email')).first()
    if not user or not user.check_password(data.get('password')):
        return jsonify({'msg': 'Invalid credentials'}), 401

    if not user.is_active:
        return jsonify({'msg': 'Account is disabled'}), 401

    user.last_login = datetime.utcnow()
    db.session.commit()

    # Audit log
    from app.models import AuditLog
    log = AuditLog(
        user_id=user.id,
        action='login',
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string
    )
    db.session.add(log)
    db.session.commit()

    tokens = user.get_tokens()
    return jsonify(tokens), 200

@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    user_id = get_jwt_identity()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'msg': 'User not found'}), 401
    new_access = create_access_token(identity=user_id)
    return jsonify({'access_token': new_access}), 200

@bp.route('/me', methods=['GET'])
@auth_jwt_required
def get_me():
    from .users import user_schema
    return jsonify(user_schema.dump(g.current_user)), 200

@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # Optionally blacklist token
    jti = get_jwt()['jti']
    # Store in blacklist (requires blacklist model)
    # For now, just return success
    return jsonify({'msg': 'Logged out'}), 200
