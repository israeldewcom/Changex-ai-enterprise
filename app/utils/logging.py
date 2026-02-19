"""
Structured logging configuration.
"""
import logging
import logging.config
import json
import sys
from flask import request, has_request_context
from pythonjsonlogger import jsonlogger
from datetime import datetime

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with extra fields."""
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat()
        if has_request_context():
            log_record['ip'] = request.remote_addr
            log_record['method'] = request.method
            log_record['path'] = request.path
            log_record['user_agent'] = request.user_agent.string
        log_record['level'] = record.levelname
        log_record['logger'] = record.name

def configure_logging(app):
    """Configure logging for the application."""
    log_level = app.config.get('LOG_LEVEL', 'INFO')
    log_format = app.config.get('LOG_FORMAT', 'json')
    log_file = app.config.get('LOG_FILE')
    
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if log_format == 'json':
        formatter = CustomJsonFormatter('%(timestamp)s %(level)s %(name)s %(message)s')
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    console_handler.setFormatter(formatter)
    handlers.append(console_handler)
    
    # File handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(level=log_level, handlers=handlers)
    
    # Set levels for third-party libraries
    logging.getLogger('werkzeug').setLevel(log_level)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
