from flask import Blueprint, request, jsonify, g
from app import db
from app.models import Assignment, Submission, AssignmentGroup, Enrollment
from app.auth import jwt_required, faculty_required, student_required, institution_member_required
from app.utils.s3 import upload_file_to_s3
from app.services.grading import calculate_final_grade
from app.utils.validators import AssignmentCreateSchema
from marshmallow import ValidationError
from datetime import datetime
import logging

bp = Blueprint('assignments', __name__)
logger = logging.getLogger(__name__)

@bp.route('', methods=['POST'])
@jwt_required
@faculty_required(institution_id_param='institution_id')
def create_assignment():
    schema = AssignmentCreateSchema()
    try:
        data = schema.load(request.json)
    except ValidationError as e:
        return jsonify({'errors': e.messages}), 400

    assignment = Assignment(
        course_offering_id=data['course_offering_id'],
        group_id=data.get('group_id'),
        title=data['title'],
        description=data.get('description'),
        due_date=data['due_date'],
        points_possible=data.get('points_possible', 100),
        rubric=data.get('rubric'),
        submission_type=data.get('submission_type', 'file'),
        allowed_file_types=data.get('allowed_file_types', []),
        max_file_size=data.get('max_file_size', 10485760),
        late_policy=data.get('late_policy', 'not_allowed'),
        late_penalty=data.get('late_penalty', 0.10)
    )
    db.session.add(assignment)
    db.session.commit()
    logger.info(f"Assignment created: {assignment.id}")
    return jsonify(assignment.to_dict()), 201

@bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_assignment(id):
    assignment = db.session.get(Assignment, id)
    if not assignment:
        return jsonify({'msg': 'Assignment not found'}), 404
    return jsonify(assignment.to_dict())

@bp.route('/<int:id>/submit', methods=['POST'])
@jwt_required
@student_required(institution_id_param='institution_id')
def submit_assignment(id):
    assignment = db.session.get(Assignment, id)
    if not assignment:
        return jsonify({'msg': 'Assignment not found'}), 404

    # Check if already submitted
    existing = Submission.query.filter_by(assignment_id=id, user_id=g.current_user.id).first()
    if existing:
        return jsonify({'msg': 'Already submitted'}), 400

    # Check due date and late policy
    now = datetime.utcnow()
    status = 'submitted'
    if now > assignment.due_date:
        if assignment.late_policy == 'not_allowed':
            return jsonify({'msg': 'Late submissions not allowed'}), 400
        elif assignment.late_policy == 'allowed_with_penalty':
            status = 'late'

    # Handle file upload
    file_url = None
    if assignment.submission_type == 'file':
        if 'file' not in request.files:
            return jsonify({'msg': 'File required'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'msg': 'No file selected'}), 400
        # Validate file type and size
        if assignment.allowed_file_types:
            ext = file.filename.rsplit('.', 1)[-1].lower()
            if ext not in assignment.allowed_file_types:
                return jsonify({'msg': 'File type not allowed'}), 400
        file.seek(0, os.SEEK_END)
        size = file.tell()
        if size > assignment.max_file_size:
            return jsonify({'msg': 'File too large'}), 400
        file.seek(0)
        file_url = upload_file_to_s3(file, folder='submissions')
        if not file_url:
            return jsonify({'msg': 'File upload failed'}), 500

    submission = Submission(
        assignment_id=id,
        user_id=g.current_user.id,
        file_url=file_url,
        text=request.form.get('text'),
        submitted_at=now,
        status=status
    )
    db.session.add(submission)
    db.session.commit()

    logger.info(f"Submission created: {submission.id} for assignment {id}")
    return jsonify({'msg': 'Submitted', 'submission_id': submission.id}), 201

@bp.route('/submissions/<int:submission_id>/grade', methods=['POST'])
@jwt_required
@faculty_required(institution_id_param='institution_id')
def grade_submission(submission_id):
    submission = db.session.get(Submission, submission_id)
    if not submission:
        return jsonify({'msg': 'Submission not found'}), 404

    data = request.get_json()
    grade = data.get('grade')
    feedback = data.get('feedback')

    if grade is not None:
        submission.grade = grade
        submission.feedback = feedback
        submission.graded_at = datetime.utcnow()
        submission.status = 'graded'
        db.session.commit()

        # Recalculate final grade for enrollment
        enrollment = Enrollment.query.filter_by(
            user_id=submission.user_id,
            course_offering_id=submission.assignment.course_offering_id
        ).first()
        if enrollment:
            calculate_final_grade(enrollment.id)

        logger.info(f"Submission {submission_id} graded: {grade}")
    return jsonify({'msg': 'Graded'}), 200
