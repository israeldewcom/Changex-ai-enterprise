from flask import Blueprint, request, jsonify, g
from app import db
from app.models import Course, CourseOffering, Enrollment, User, Assignment
from app.auth import jwt_required, faculty_required, admin_required, student_required, institution_member_required
from app.services.enrollment import enroll_student
from app.utils.pagination import paginate
from app.utils.validators import CourseCreateSchema
from marshmallow import ValidationError
from app.extensions import cache

bp = Blueprint('courses', __name__)

class CourseSchema:
    pass  # Define as needed

@bp.route('', methods=['POST'])
@jwt_required
@faculty_required(institution_id_param='institution_id')
def create_course():
    schema = CourseCreateSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as e:
        return jsonify({'errors': e.messages}), 400

    course = Course(
        institution_id=data['institution_id'],
        department_id=data.get('department_id'),
        code=data['code'],
        title=data['title'],
        description=data.get('description'),
        credits=data.get('credits', 3),
        syllabus=data.get('syllabus', {})
    )
    db.session.add(course)
    db.session.commit()
    return jsonify(course.to_dict()), 201

@bp.route('/<int:id>', methods=['GET'])
@jwt_required
@cache.cached(timeout=60)
def get_course(id):
    course = db.session.get(Course, id)
    if not course:
        return jsonify({'msg': 'Course not found'}), 404
    return jsonify(course.to_dict())

@bp.route('/<int:id>/offerings', methods=['GET'])
@jwt_required
def get_offerings(id):
    offerings = CourseOffering.query.filter_by(course_id=id).all()
    return jsonify([o.to_dict() for o in offerings])

@bp.route('/offerings/<int:offering_id>', methods=['GET'])
@jwt_required
def get_offering(offering_id):
    offering = db.session.get(CourseOffering, offering_id)
    if not offering:
        return jsonify({'msg': 'Offering not found'}), 404
    return jsonify(offering.to_dict())

@bp.route('/offerings/<int:offering_id>/enroll', methods=['POST'])
@jwt_required
@student_required(institution_id_param='institution_id')
def enroll(offering_id):
    data = request.get_json()
    institution_id = data.get('institution_id')
    if not institution_id:
        return jsonify({'msg': 'institution_id required'}), 400

    result = enroll_student(g.current_user.id, offering_id)
    if 'error' in result:
        return jsonify({'msg': result['error']}), result.get('code', 400)
    return jsonify(result), 201

@bp.route('/offerings/<int:offering_id>/students', methods=['GET'])
@jwt_required
@institution_member_required(institution_id_param='institution_id')
def list_students(offering_id):
    offering = db.session.get(CourseOffering, offering_id)
    if not offering:
        return jsonify({'msg': 'Offering not found'}), 404
    # Check if user is instructor or admin
    if offering.instructor_id != g.current_user.id:
        # Check admin role (already done by decorator, but we need institution_id)
        # We'll assume decorator already verified membership, but we need to ensure faculty/instructor
        # For simplicity, allow any member? Better to check if user is faculty in this institution.
        # We'll rely on decorator requiring institution membership, but we might want faculty_required
        # For now, allow members to see student list? Probably not. We'll change to faculty_required.
        return jsonify({'msg': 'Permission denied'}), 403

    enrollments = Enrollment.query.filter_by(course_offering_id=offering_id, status='enrolled').all()
    students = [{'id': e.user.id, 'name': e.user.full_name, 'email': e.user.email} for e in enrollments]
    return jsonify(students)
