"""
Prometheus metrics integration.
"""
from prometheus_flask_exporter import PrometheusMetrics
from app.extensions import prometheus_metrics

def init_metrics(app):
    """Initialize Prometheus metrics."""
    if app.config['PROMETHEUS_ENABLED']:
        prometheus_metrics.init_app(app)
        # Add custom metrics
        prometheus_metrics.info('app_info', 'ChangeX Eduspace', version='1.0')
