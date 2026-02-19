"""
Enrollment business logic.
"""
from app import db
from app.models import Enrollment, CourseOffering, Waitlist, Course
from app.services.notification import notify_user
from app.services.realtime import send_course_update
from sqlalchemy import and_
import logging

logger = logging.getLogger(__name__)

def enroll_student(user_id: int, offering_id: int) -> dict:
    """
    Enroll a student in a course offering.
    Handles prerequisites, capacity, waitlist.
    """
    offering = db.session.get(CourseOffering, offering_id)
    if not offering:
        return {'error': 'Offering not found', 'code': 404}

    # Check if already enrolled
    existing = Enrollment.query.filter_by(
        user_id=user_id, 
        course_offering_id=offering_id
    ).first()
    if existing:
        return {'error': 'Already enrolled', 'code': 400}

    # Check capacity
    enrolled_count = Enrollment.query.filter_by(
        course_offering_id=offering_id, 
        status='enrolled'
    ).count()
    if enrolled_count >= offering.capacity:
        # Add to waitlist
        waitlist_entry = Waitlist(
            user_id=user_id, 
            course_offering_id=offering_id
        )
        db.session.add(waitlist_entry)
        db.session.commit()
        logger.info(f"User {user_id} added to waitlist for offering {offering_id}")
        # Notify
        notify_user.delay(
            user_id, 
            'waitlist_added', 
            {'offering_id': offering_id, 'course': offering.course.title}
        )
        return {'message': 'Course full, added to waitlist', 'waitlist': True}

    # Check prerequisites
    course = offering.course
    if course.prerequisites:
        # Get completed courses for user (grades >= passing)
        completed = Enrollment.query.filter(
            Enrollment.user_id == user_id,
            Enrollment.status == 'completed',
            Enrollment.grade >= 60.0
        ).join(CourseOffering).join(Course).with_entities(Course.id).all()
        completed_ids = {c[0] for c in completed}
        prereq_ids = {p.id for p in course.prerequisites}
        if not prereq_ids.issubset(completed_ids):
            logger.warning(f"User {user_id} failed prerequisites for {course.code}")
            return {'error': 'Prerequisites not met', 'code': 400}

    # Enroll
    enrollment = Enrollment(
        user_id=user_id, 
        course_offering_id=offering_id, 
        status='enrolled'
    )
    db.session.add(enrollment)
    db.session.commit()

    logger.info(f"User {user_id} enrolled in offering {offering_id}")

    # Send notifications
    notify_user.delay(
        user_id, 
        'enrollment_success', 
        {'offering_id': offering_id, 'course': offering.course.title}
    )
    # Real-time update to course room
    send_course_update.delay(
        offering_id, 
        'enrollment_change', 
        {'user_id': user_id, 'status': 'enrolled'}
    )

    return {'enrollment_id': enrollment.id}
