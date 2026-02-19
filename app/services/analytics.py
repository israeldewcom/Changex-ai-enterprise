"""
Analytics and reporting services.
"""
from app import db
from app.models import (
    Institution, User, Course, Enrollment, Submission, 
    Attendance, Payment, UserRole, Role
)
from sqlalchemy import func, and_
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

def institution_stats(institution_id: int) -> dict:
    """
    Get aggregated stats for an institution.
    """
    # Count users by role
    students = db.session.query(func.count(UserRole.id)).filter(
        UserRole.institution_id == institution_id,
        UserRole.role.has(Role.name == 'student')
    ).scalar() or 0
    
    faculty = db.session.query(func.count(UserRole.id)).filter(
        UserRole.institution_id == institution_id,
        UserRole.role.has(Role.name == 'faculty')
    ).scalar() or 0
    
    # Courses and offerings
    courses = Course.query.filter_by(institution_id=institution_id).count()
    active_offerings = Course.query.join(CourseOffering).filter(
        Course.institution_id == institution_id,
        CourseOffering.status == 'active'
    ).count()
    
    # Enrollments
    enrollments = db.session.query(func.count(Enrollment.id)).join(
        CourseOffering
    ).join(Course).filter(
        Course.institution_id == institution_id,
        Enrollment.status == 'enrolled'
    ).scalar() or 0
    
    # Revenue (completed payments)
    revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.institution_id == institution_id,
        Payment.status == 'completed'
    ).scalar() or 0
    
    return {
        'students': students,
        'faculty': faculty,
        'courses': courses,
        'active_offerings': active_offerings,
        'enrollments': enrollments,
        'revenue': float(revenue)
    }

def course_performance(course_offering_id: int) -> dict:
    """
    Get performance metrics for a specific course offering.
    """
    offering = CourseOffering.query.get(course_offering_id)
    if not offering:
        return {}
    
    enrollments = Enrollment.query.filter_by(
        course_offering_id=course_offering_id,
        status='enrolled'
    ).all()
    
    if not enrollments:
        return {}
    
    avg_grade = sum(e.grade or 0 for e in enrollments) / len(enrollments)
    pass_rate = sum(1 for e in enrollments if (e.grade or 0) >= 60) / len(enrollments)
    
    # Attendance rate
    total_classes = Attendance.query.filter_by(
        course_offering_id=course_offering_id
    ).distinct(Attendance.date).count()
    if total_classes > 0:
        attended = Attendance.query.filter_by(
            course_offering_id=course_offering_id,
            status='present'
        ).count()
        attendance_rate = attended / (total_classes * len(enrollments))
    else:
        attendance_rate = 0
    
    # Submission rate
    total_assignments = offering.assignments.count()
    if total_assignments > 0:
        submitted = Submission.query.join(Assignment).filter(
            Assignment.course_offering_id == course_offering_id
        ).count()
        submission_rate = submitted / (total_assignments * len(enrollments))
    else:
        submission_rate = 0
    
    return {
        'avg_grade': avg_grade,
        'pass_rate': pass_rate,
        'attendance_rate': attendance_rate,
        'submission_rate': submission_rate,
        'enrollment_count': len(enrollments)
    }

def user_activity(user_id: int, days: int = 30) -> dict:
    """
    Get user activity metrics over last N days.
    """
    since = datetime.utcnow() - timedelta(days=days)
    
    # Logins (from audit logs)
    logins = AuditLog.query.filter(
        AuditLog.user_id == user_id,
        AuditLog.action == 'login',
        AuditLog.created_at >= since
    ).count()
    
    # Submissions
    submissions = Submission.query.filter(
        Submission.user_id == user_id,
        Submission.submitted_at >= since
    ).count()
    
    # Attendance
    attendance = Attendance.query.filter(
        Attendance.user_id == user_id,
        Attendance.created_at >= since
    ).count()
    
    return {
        'logins': logins,
        'submissions': submissions,
        'attendance': attendance,
        'active_days': (datetime.utcnow() - since).days
    }
