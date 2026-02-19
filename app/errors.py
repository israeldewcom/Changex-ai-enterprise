"""
Custom error classes and global error handlers.
"""
from flask import jsonify, current_app
from werkzeug.exceptions import HTTPException
from app.extensions import db
import logging

logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base API exception."""
    status_code = 400
    message = "An error occurred"

    def __init__(self, message: str = None, status_code: int = None,
                 payload: dict = None):
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self) -> dict:
        rv = dict(self.payload or ())
        rv['message'] = self.message
        rv['status'] = 'error'
        return rv


class ValidationError(APIError):
    status_code = 400
    message = "Validation error"


class AuthenticationError(APIError):
    status_code = 401
    message = "Authentication failed"


class AuthorizationError(APIError):
    status_code = 403
    message = "Permission denied"


class NotFoundError(APIError):
    status_code = 404
    message = "Resource not found"


class ConflictError(APIError):
    status_code = 409
    message = "Resource conflict"


class RateLimitError(APIError):
    status_code = 429
    message = "Rate limit exceeded"


def register_error_handlers(app):
    """Register error handlers for the Flask app."""
    @app.errorhandler(APIError)
    def handle_api_error(error):
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(error):
        response = jsonify({
            'message': error.description,
            'status': 'error'
        })
        response.status_code = error.code
        return response

    @app.errorhandler(Exception)
    def handle_unhandled_error(error):
        logger.exception("Unhandled exception")
        db.session.rollback()
        if app.config.get('SENTRY_DSN'):
            from sentry_sdk import capture_exception
            capture_exception(error)
        response = jsonify({
            'message': 'Internal server error',
            'status': 'error'
        })
        response.status_code = 500
        return response
