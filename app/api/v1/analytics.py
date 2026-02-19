from flask import Blueprint, request, jsonify, g
from app import db
from app.models import Enrollment, CourseOffering, Course, User, Submission, Attendance, Role, UserRole
from app.services.predictive import at_risk_prediction
from app.services.analytics import institution_stats, course_performance, user_activity
from app.auth import jwt_required, faculty_required, admin_required, institution_member_required
from sqlalchemy import func
import logging

bp = Blueprint('analytics', __name__)
logger = logging.getLogger(__name__)

@bp.route('/course/<int:offering_id>/at-risk', methods=['GET'])
@jwt_required
@faculty_required(institution_id_param='institution_id')
def at_risk(offering_id):
    offering = db.session.get(CourseOffering, offering_id)
    if not offering:
        return jsonify({'msg': 'Offering not found'}), 404

    # Get all enrolled students
    enrollments = Enrollment.query.filter_by(course_offering_id=offering_id, status='enrolled').all()
    if not enrollments:
        return jsonify([])

    student_features = []
    for e in enrollments:
        # Calculate avg grade from submissions
        submissions = Submission.query.join(Assignment).filter(
            Assignment.course_offering_id == offering_id,
            Submission.user_id == e.user_id,
            Submission.grade.isnot(None)
        ).all()
        if submissions:
            avg_grade = sum(s.grade for s in submissions) / len(submissions)
        else:
            avg_grade = 0

        # Submission rate (submitted vs total assignments)
        total_assignments = len(offering.assignments)
        submitted = Submission.query.filter(
            Submission.user_id == e.user_id,
            Submission.assignment_id.in_([a.id for a in offering.assignments])
        ).count()
        submission_rate = submitted / total_assignments if total_assignments else 0

        # Attendance rate
        attended = Attendance.query.filter_by(
            course_offering_id=offering_id,
            user_id=e.user_id,
            status='present'
        ).count()
        total_classes = Attendance.query.filter_by(course_offering_id=offering_id).distinct(Attendance.date).count()
        attendance_rate = attended / total_classes if total_classes else 0

        student_features.append({
            'student_id': e.user_id,
            'avg_grade': avg_grade,
            'submission_rate': submission_rate,
            'attendance': attendance_rate
        })

    risk_scores = at_risk_prediction(student_features)
    return jsonify(risk_scores)

@bp.route('/institution/<int:institution_id>/summary', methods=['GET'])
@jwt_required
@admin_required(institution_id_param='institution_id')
def institution_summary(institution_id):
    stats = institution_stats(institution_id)
    return jsonify(stats)

@bp.route('/course/<int:offering_id>/performance', methods=['GET'])
@jwt_required
@faculty_required(institution_id_param='institution_id')
def course_performance_endpoint(offering_id):
    perf = course_performance(offering_id)
    return jsonify(perf)

@bp.route('/user/<int:user_id>/activity', methods=['GET'])
@jwt_required
def user_activity_endpoint(user_id):
    # Only allow if user is self or admin
    if user_id != g.current_user.id:
        # Check admin in any institution? For simplicity, allow only self
        return jsonify({'msg': 'Permission denied'}), 403
    activity = user_activity(user_id)
    return jsonify(activity)
