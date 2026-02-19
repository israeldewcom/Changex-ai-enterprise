"""
Grading and grade calculation services.
"""
from app import db
from app.models import Enrollment, Assignment, Submission, Grade, AssignmentGroup
import logging

logger = logging.getLogger(__name__)

def calculate_final_grade(enrollment_id: int) -> float:
    """
    Calculate final grade for an enrollment based on assignment groups.
    Returns percentage.
    """
    enrollment = db.session.get(Enrollment, enrollment_id)
    if not enrollment:
        return None

    offering = enrollment.course_offering
    groups = offering.assignment_groups.all()
    
    if not groups:
        # No groups, use average of all submissions?
        submissions = Submission.query.join(Assignment).filter(
            Assignment.course_offering_id == offering.id,
            Submission.user_id == enrollment.user_id,
            Submission.grade.isnot(None)
        ).all()
        if not submissions:
            enrollment.grade = 0
            enrollment.letter_grade = 'F'
            db.session.commit()
            return 0
        total = sum(s.grade for s in submissions)
        possible = sum(s.assignment.points_possible for s in submissions)
        percentage = (total / possible) * 100 if possible > 0 else 0
        enrollment.grade = percentage
        enrollment.letter_grade = percentage_to_letter(percentage)
        db.session.commit()
        return percentage

    total_weight = 0
    weighted_sum = 0

    for group in groups:
        assignments = group.assignments.all()
        # Get all submissions for this user in this group
        group_submissions = Submission.query.filter(
            Submission.assignment_id.in_([a.id for a in assignments]),
            Submission.user_id == enrollment.user_id,
            Submission.grade.isnot(None)
        ).all()
        
        if not group_submissions:
            continue
        
        # Calculate group grade (consider dropping lowest)
        grades = [(s.grade, s.assignment.points_possible) for s in group_submissions]
        if group.drop_lowest > 0:
            # Sort by percentage and drop lowest
            grades.sort(key=lambda x: x[0]/x[1] if x[1]>0 else 0)
            grades = grades[group.drop_lowest:]
        
        total_points = sum(g[0] for g in grades)
        total_possible = sum(g[1] for g in grades)
        group_percentage = (total_points / total_possible) if total_possible > 0 else 0
        
        weighted_sum += group_percentage * group.weight
        total_weight += group.weight

    if total_weight > 0:
        final_percentage = (weighted_sum / total_weight) * 100
    else:
        final_percentage = 0

    enrollment.grade = final_percentage
    enrollment.letter_grade = percentage_to_letter(final_percentage)
    db.session.commit()
    
    logger.info(f"Final grade calculated for enrollment {enrollment_id}: {final_percentage}%")
    return final_percentage

def percentage_to_letter(percentage: float) -> str:
    """Convert percentage to letter grade."""
    if percentage >= 90:
        return 'A'
    elif percentage >= 80:
        return 'B'
    elif percentage >= 70:
        return 'C'
    elif percentage >= 60:
        return 'D'
    else:
        return 'F'
