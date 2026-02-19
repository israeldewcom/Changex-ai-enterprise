"""
GDPR compliance utilities: consent tracking, data anonymization, export.
"""
from datetime import datetime, timedelta
from app.extensions import db
from app.models import GDPRConsent, User
import json
import csv
from io import StringIO

def record_consent(user_id: int, consent_type: str, given: bool, ip: str = None, user_agent: str = None):
    """Record a consent action."""
    consent = GDPRConsent(
        user_id=user_id,
        consent_type=consent_type,
        given=given,
        ip_address=ip,
        user_agent=user_agent,
        expires_at=datetime.utcnow() + timedelta(days=365) if given else None
    )
    db.session.add(consent)
    db.session.commit()

def get_user_consent(user_id: int, consent_type: str) -> bool:
    """Check if user has given valid consent."""
    latest = GDPRConsent.query.filter_by(
        user_id=user_id,
        consent_type=consent_type
    ).order_by(GDPRConsent.created_at.desc()).first()
    if not latest:
        return False
    if latest.expires_at and latest.expires_at < datetime.utcnow():
        return False
    return latest.given

def anonymize_user(user_id: int):
    """Anonymize a user's personal data (for deletion requests)."""
    user = User.query.get(user_id)
    if not user:
        return
    user.email = f"deleted-{user_id}@anonymous.changex"
    user.full_name = "Deleted User"
    user.profile = {}
    # Optionally delete related data? Keep for analytics but anonymized.
    db.session.commit()

def export_user_data(user_id: int) -> str:
    """Export all user data as CSV."""
    user = User.query.get(user_id)
    if not user:
        return ""
    
    output = StringIO()
    writer = csv.writer(output)
    
    # User profile
    writer.writerow(['Field', 'Value'])
    writer.writerow(['Email', user.email])
    writer.writerow(['Full Name', user.full_name])
    writer.writerow(['Created At', user.created_at])
    
    # Enrollments
    writer.writerow([])
    writer.writerow(['Enrollments'])
    writer.writerow(['Course', 'Status', 'Grade'])
    for e in user.enrollments:
        writer.writerow([e.course_offering.course.title, e.status, e.grade])
    
    # Submissions
    writer.writerow([])
    writer.writerow(['Submissions'])
    writer.writerow(['Assignment', 'Submitted', 'Grade'])
    for s in user.submissions:
        writer.writerow([s.assignment.title, s.submitted_at, s.grade])
    
    # Payments
    writer.writerow([])
    writer.writerow(['Payments'])
    writer.writerow(['Amount', 'Status', 'Date'])
    for p in user.payments:
        writer.writerow([p.amount, p.status, p.created_at])
    
    return output.getvalue()
