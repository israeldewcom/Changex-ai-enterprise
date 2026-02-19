"""
Authentication and authorization decorators.
"""
from functools import wraps
from typing import Callable, Optional, Any
from flask import request, jsonify, g
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from app.models import User, UserRole, Role
from app.extensions import db
import logging

logger = logging.getLogger(__name__)


def jwt_required(fn: Callable) -> Callable:
    """Require a valid JWT token, sets g.current_user."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = db.session.get(User, user_id)
            if not user or not user.is_active:
                logger.warning(f"JWT auth failed: user {user_id} not found or inactive")
                return jsonify({'msg': 'User not found or inactive'}), 401
            g.current_user = user
            g.jwt_claims = get_jwt()
        except Exception as e:
            logger.error(f"JWT error: {e}")
            return jsonify({'msg': 'Invalid token'}), 401
        return fn(*args, **kwargs)
    return wrapper


def role_required(required_role: str,
                  institution_id_param: str = 'institution_id',
                  allow_admin: bool = True) -> Callable:
    """
    Check if user has required role in institution.
    If allow_admin, admin role bypasses.
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Get institution_id from kwargs, json, or args
            inst_id = (kwargs.get(institution_id_param) or
                       request.json.get('institution_id') if request.json else None or
                       request.args.get('institution_id'))
            if not inst_id:
                return jsonify({'msg': 'Institution ID required'}), 400

            # Check if user has admin role (if allowed)
            if allow_admin:
                admin_role = UserRole.query.filter_by(
                    user_id=g.current_user.id,
                    institution_id=inst_id
                ).join(Role).filter(Role.name == 'admin').first()
                if admin_role:
                    return fn(*args, **kwargs)

            # Check for required role
            user_role = UserRole.query.filter_by(
                user_id=g.current_user.id,
                institution_id=inst_id
            ).join(Role).filter(Role.name == required_role).first()
            if not user_role:
                return jsonify({'msg': f'Role {required_role} required in this institution'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def permissions_required(permission: str,
                         institution_id_param: str = 'institution_id') -> Callable:
    """Check if user has specific permission in institution via role permissions."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            inst_id = (kwargs.get(institution_id_param) or
                       request.json.get('institution_id') if request.json else None or
                       request.args.get('institution_id'))
            if not inst_id:
                return jsonify({'msg': 'Institution ID required'}), 400
            user_roles = UserRole.query.filter_by(
                user_id=g.current_user.id,
                institution_id=inst_id
            ).all()
            for ur in user_roles:
                if permission in ur.role.permissions or '*' in ur.role.permissions:
                    return fn(*args, **kwargs)
            return jsonify({'msg': 'Permission denied'}), 403
        return wrapper
    return decorator


def admin_required(institution_id_param: str = 'institution_id') -> Callable:
    """Convenience decorator for admin role."""
    return role_required('admin', institution_id_param)


def faculty_required(institution_id_param: str = 'institution_id') -> Callable:
    return role_required('faculty', institution_id_param)


def student_required(institution_id_param: str = 'institution_id') -> Callable:
    return role_required('student', institution_id_param)


def parent_required(institution_id_param: str = 'institution_id') -> Callable:
    return role_required('parent', institution_id_param)


def institution_member_required(institution_id_param: str = 'institution_id') -> Callable:
    """Check if user has any role in the institution."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            inst_id = (kwargs.get(institution_id_param) or
                       request.json.get('institution_id') if request.json else None or
                       request.args.get('institution_id'))
            if not inst_id:
                return jsonify({'msg': 'Institution ID required'}), 400
            user_role = UserRole.query.filter_by(
                user_id=g.current_user.id,
                institution_id=inst_id
            ).first()
            if not user_role:
                return jsonify({'msg': 'User not a member of this institution'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def parent_of_student(student_id_param: str = 'student_id') -> Callable:
    """Check if current user is parent of the student specified in URL."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            student_id = kwargs.get(student_id_param) or request.args.get(student_id_param)
            if not student_id:
                return jsonify({'msg': 'Student ID required'}), 400
            student = db.session.get(User, student_id)
            if not student:
                return jsonify({'msg': 'Student not found'}), 404
            if g.current_user not in student.parents:
                return jsonify({'msg': 'You are not a parent of this student'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def platform_admin_required() -> Callable:
    """Check if user has platform-wide admin role (institution_id=None)."""
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            platform_admin = UserRole.query.filter_by(
                user_id=g.current_user.id,
                institution_id=None
            ).join(Role).filter(Role.name == 'platform_admin').first()
            if not platform_admin:
                return jsonify({'msg': 'Platform admin required'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
