import os
from datetime import timedelta
from typing import Optional, Dict, Any
import logging

class Config:
    # Flask
    SECRET_KEY: str = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
    ENV: str = os.environ.get('FLASK_ENV', 'production')
    DEBUG: bool = os.environ.get('FLASK_DEBUG', '0') == '1'
    TESTING: bool = False
    PROPAGATE_EXCEPTIONS: bool = True

    # Database
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        'DATABASE_URL', 
        'postgresql://user:pass@db:5432/changex'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: Dict[str, Any] = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
        'pool_recycle': 300,
        'pool_pre_ping': True,
        'max_overflow': 20,
    }

    # JWT
    JWT_SECRET_KEY: str = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change')
    JWT_ACCESS_TOKEN_EXPIRES: timedelta = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES: timedelta = timedelta(days=30)
    JWT_TOKEN_LOCATION: list = ['headers']
    JWT_HEADER_NAME: str = 'Authorization'
    JWT_HEADER_TYPE: str = 'Bearer'
    JWT_BLACKLIST_ENABLED: bool = True
    JWT_BLACKLIST_TOKEN_CHECKS: list = ['access', 'refresh']

    # Redis & Caching
    REDIS_URL: str = os.environ.get('REDIS_URL', 'redis://redis:6379/0')
    CACHE_TYPE: str = 'RedisCache'
    CACHE_REDIS_URL: str = REDIS_URL
    CACHE_DEFAULT_TIMEOUT: int = 300
    CACHE_KEY_PREFIX: str = 'changex_cache_'

    # Celery
    CELERY_BROKER_URL: str = REDIS_URL
    CELERY_RESULT_BACKEND: str = REDIS_URL
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 30 * 60
    CELERY_ACCEPT_CONTENT: list = ['json']
    CELERY_TASK_SERIALIZER: str = 'json'
    CELERY_RESULT_SERIALIZER: str = 'json'

    # Rate Limiting
    RATELIMIT_ENABLED: bool = True
    RATELIMIT_STORAGE_URL: str = REDIS_URL
    RATELIMIT_STRATEGY: str = 'fixed-window'
    RATELIMIT_DEFAULT: str = '200 per day;50 per hour'

    # Security
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'
    REMEMBER_COOKIE_SECURE: bool = True
    REMEMBER_COOKIE_HTTPONLY: bool = True
    PERMANENT_SESSION_LIFETIME: int = 3600
    SECURITY_HEADERS: Dict[str, str] = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'SAMEORIGIN',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
    }
    CSP_POLICY: Dict[str, Any] = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'"],  # Adjust for production
        'style-src': ["'self'", "'unsafe-inline'"],
        'img-src': ["'self'", "data:", "https:"],
        'font-src': ["'self'"],
        'connect-src': ["'self'"],
    }

    # File storage (AWS S3)
    AWS_ACCESS_KEY_ID: Optional[str] = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_S3_BUCKET: str = os.environ.get('AWS_S3_BUCKET', 'changex-eduspace')
    AWS_REGION: str = os.environ.get('AWS_REGION', 'us-east-1')
    AWS_S3_MAX_SIZE: int = 100 * 1024 * 1024  # 100 MB

    # Email (SendGrid)
    MAIL_SERVER: str = os.environ.get('MAIL_SERVER', 'smtp.sendgrid.net')
    MAIL_PORT: int = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS: bool = True
    MAIL_USE_SSL: bool = False
    MAIL_USERNAME: str = os.environ.get('MAIL_USERNAME', 'apikey')
    MAIL_PASSWORD: str = os.environ.get('SENDGRID_API_KEY', '')
    MAIL_DEFAULT_SENDER: str = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@changex.com')
    MAIL_MAX_EMAILS: Optional[int] = None
    MAIL_ASCII_ATTACHMENTS: bool = False

    # SMS (Twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN: Optional[str] = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER: Optional[str] = os.environ.get('TWILIO_PHONE_NUMBER')

    # Payment (Stripe)
    STRIPE_SECRET_KEY: Optional[str] = os.environ.get('STRIPE_SECRET_KEY')
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.environ.get('STRIPE_WEBHOOK_SECRET')
    STRIPE_CURRENCY: str = os.environ.get('STRIPE_CURRENCY', 'usd')

    # Monitoring & Error Tracking
    SENTRY_DSN: Optional[str] = os.environ.get('SENTRY_DSN')
    PROMETHEUS_ENABLED: bool = os.environ.get('PROMETHEUS_ENABLED', '0') == '1'
    PROMETHEUS_PORT: int = int(os.environ.get('PROMETHEUS_PORT', 8000))

    # Logging
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = os.environ.get('LOG_FORMAT', 'json')  # 'json' or 'text'
    LOG_FILE: Optional[str] = os.environ.get('LOG_FILE')  # optional file path

    # Feature Flags
    FEATURE_FLAGS: Dict[str, bool] = {
        'predictive_analytics': os.environ.get('FEATURE_PREDICTIVE', '1') == '1',
        'realtime_notifications': os.environ.get('FEATURE_REALTIME', '1') == '1',
        'gamification': os.environ.get('FEATURE_GAMIFICATION', '0') == '1',
    }

    # Compliance (GDPR)
    GDPR_CONSENT_REQUIRED: bool = os.environ.get('GDPR_CONSENT_REQUIRED', '1') == '1'
    DATA_RETENTION_DAYS: int = int(os.environ.get('DATA_RETENTION_DAYS', 365))
    ANONYMIZE_AFTER_DAYS: int = int(os.environ.get('ANONYMIZE_AFTER_DAYS', 730))

    # WebSocket (SocketIO)
    SOCKETIO_MESSAGE_QUEUE: Optional[str] = os.environ.get('SOCKETIO_MESSAGE_QUEUE', REDIS_URL)
    SOCKETIO_CORS_ALLOWED_ORIGINS: list = os.environ.get('SOCKETIO_CORS', '*').split(',')

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    @classmethod
    def get_feature_flag(cls, name: str) -> bool:
        return cls.FEATURE_FLAGS.get(name, False)

class DevelopmentConfig(Config):
    DEBUG: bool = True
    SQLALCHEMY_ECHO: bool = True
    SESSION_COOKIE_SECURE: bool = False
    REMEMBER_COOKIE_SECURE: bool = False
    RATELIMIT_ENABLED: bool = False
    SECURITY_HEADERS: Dict[str, str] = {}  # Disable HSTS in dev
    CSP_POLICY: Dict[str, Any] = {}  # Disable CSP in dev

class TestingConfig(Config):
    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = 'sqlite:///:memory:'
    CACHE_TYPE: str = 'NullCache'
    RATELIMIT_ENABLED: bool = False
    WTF_CSRF_ENABLED: bool = False
    JWT_BLACKLIST_ENABLED: bool = False
    SESSION_COOKIE_SECURE: bool = False
    REMEMBER_COOKIE_SECURE: bool = False
    SECURITY_HEADERS: Dict[str, str] = {}
    CSP_POLICY: Dict[str, Any] = {}
    FEATURE_FLAGS: Dict[str, bool] = {k: False for k in Config.FEATURE_FLAGS}

class ProductionConfig(Config):
    DEBUG: bool = False
    TESTING: bool = False
    # Production-specific overrides can go here

config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig if os.environ.get('FLASK_ENV') != 'production' else ProductionConfig,
}
