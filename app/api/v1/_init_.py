from flask import Blueprint
from . import institutions, users, auth, courses, assignments, grades, attendance, payments, analytics, webhooks, realtime

api_bp = Blueprint('api', __name__)

api_bp.register_blueprint(institutions.bp, url_prefix='/institutions')
api_bp.register_blueprint(users.bp, url_prefix='/users')
api_bp.register_blueprint(auth.bp, url_prefix='/auth')
api_bp.register_blueprint(courses.bp, url_prefix='/courses')
api_bp.register_blueprint(assignments.bp, url_prefix='/assignments')
api_bp.register_blueprint(grades.bp, url_prefix='/grades')
api_bp.register_blueprint(attendance.bp, url_prefix='/attendance')
api_bp.register_blueprint(payments.bp, url_prefix='/payments')
api_bp.register_blueprint(analytics.bp, url_prefix='/analytics')
api_bp.register_blueprint(webhooks.bp, url_prefix='/webhooks')
api_bp.register_blueprint(realtime.bp, url_prefix='/realtime')
