"""
Services package – exposes business logic modules.
"""
from .enrollment import enroll_student
from .grading import calculate_final_grade, percentage_to_letter
from .payment import create_payment_intent, handle_webhook
from .notification import notify_user, notify_course
from .analytics import institution_stats, course_performance, user_activity
from .predictive import at_risk_prediction, train_model_async
from .realtime import send_course_update, send_user_notification, emit_notification

__all__ = [
    'enroll_student',
    'calculate_final_grade',
    'percentage_to_letter',
    'create_payment_intent',
    'handle_webhook',
    'notify_user',
    'notify_course',
    'institution_stats',
    'course_performance',
    'user_activity',
    'at_risk_prediction',
    'train_model_async',
    'send_course_update',
    'send_user_notification',
    'emit_notification',
]
