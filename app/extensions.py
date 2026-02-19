"""
Centralized extension initialization to avoid circular imports.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_caching import Cache
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO
from celery import Celery
from flask_mail import Mail
from flask_talisman import Talisman
from flask_cors import CORS
from prometheus_flask_exporter import PrometheusMetrics
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cache = Cache()
limiter = Limiter(key_func=get_remote_address)
socketio = SocketIO()
celery = Celery()
mail = Mail()
talisman = Talisman()
cors = CORS()
prometheus_metrics = PrometheusMetrics.for_app_factory()
sentry = sentry_sdk
