"""
Database models for ChangeX Eduspace.
Includes multi-tenancy, RBAC, and core educational entities.
"""
from __future__ import annotations
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any, Union
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Table, Text, Float, Numeric, Index, CheckConstraint, UniqueConstraint,
    Date, Time
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column, validates
from sqlalchemy.ext.hybrid import hybrid_property
from flask_jwt_extended import create_access_token, create_refresh_token
from werkzeug.security import generate_password_hash, check_password_hash
import re

from app.extensions import db

# Association tables with type annotations
course_prerequisites = Table(
    'course_prerequisites',
    db.metadata,
    Column('course_id', Integer, ForeignKey('courses.id'), primary_key=True),
    Column('prerequisite_id', Integer, ForeignKey('courses.id'), primary_key=True)
)

parent_child = Table(
    'parent_child',
    db.metadata,
    Column('parent_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('child_id', Integer, ForeignKey('users.id'), primary_key=True)
)


class User(db.Model):
    """User model representing all platform users."""
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    _password_hash: Mapped[str] = mapped_column("password_hash", String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    profile: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # New fields for student/alumni records
    matric_number: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    programme_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('programmes.id'))
    admission_year: Mapped[Optional[int]] = mapped_column(Integer)
    graduation_year: Mapped[Optional[int]] = mapped_column(Integer)
    next_of_kin: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)

    # Relationships (original)
    roles: Mapped[List['UserRole']] = relationship(back_populates='user', cascade='all, delete-orphan')
    enrollments: Mapped[List['Enrollment']] = relationship(back_populates='student', cascade='all, delete-orphan')
    submissions: Mapped[List['Submission']] = relationship(back_populates='student', cascade='all, delete-orphan')
    taught_courses: Mapped[List['CourseOffering']] = relationship(back_populates='instructor')
    messages_sent: Mapped[List['Message']] = relationship(foreign_keys='Message.sender_id', back_populates='sender')
    messages_received: Mapped[List['Message']] = relationship(foreign_keys='Message.recipient_id', back_populates='recipient')
    notifications: Mapped[List['Notification']] = relationship(back_populates='user', cascade='all, delete-orphan')
    payments: Mapped[List['Payment']] = relationship(back_populates='user')
    audit_logs: Mapped[List['AuditLog']] = relationship(back_populates='user')
    consent_records: Mapped[List['GDPRConsent']] = relationship(back_populates='user', cascade='all, delete-orphan')

    # New relationships
    children: Mapped[List['User']] = relationship(
        secondary=parent_child,
        primaryjoin=(parent_child.c.parent_id == id),
        secondaryjoin=(parent_child.c.child_id == id),
        backref='parents'
    )
    staff_profile: Mapped['StaffProfile'] = relationship(back_populates='user', uselist=False, cascade='all, delete-orphan')
    alumni_profile: Mapped['Alumni'] = relationship(back_populates='user', uselist=False, cascade='all, delete-orphan')
    attendance_sessions: Mapped[List['AttendanceSession']] = relationship(back_populates='user', cascade='all, delete-orphan')
    exam_sessions: Mapped[List['ExamSession']] = relationship(back_populates='user', cascade='all, delete-orphan')
    proctoring_logs: Mapped[List['ProctoringLog']] = relationship(back_populates='user', cascade='all, delete-orphan')
    borrowing_records: Mapped[List['BorrowingRecord']] = relationship(back_populates='user', cascade='all, delete-orphan')
    leave_applications: Mapped[List['LeaveApplication']] = relationship(back_populates='staff', cascade='all, delete-orphan')
    policy_acceptances: Mapped[List['UserPolicyAcceptance']] = relationship(back_populates='user', cascade='all, delete-orphan')
    hostel_applications: Mapped[List['HostelApplication']] = relationship(back_populates='student', cascade='all, delete-orphan')
    room_occupancies: Mapped[List['RoomOccupancy']] = relationship(back_populates='student', cascade='all, delete-orphan')
    registered_semesters: Mapped[List['SemesterRegistration']] = relationship(back_populates='student', cascade='all, delete-orphan')
    exam_attendances: Mapped[List['ExamAttendance']] = relationship(back_populates='student', cascade='all, delete-orphan')
    admission_applications: Mapped[List['AdmissionApplication']] = relationship(back_populates='student', cascade='all, delete-orphan')

    @property
    def password(self) -> None:
        """Prevent password from being accessed."""
        raise AttributeError('password is not readable')

    @password.setter
    def password(self, password: str) -> None:
        """Hash and set password."""
        self._password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password."""
        return check_password_hash(self._password_hash, password)

    def get_tokens(self) -> Dict[str, str]:
        """Generate JWT tokens."""
        return {
            'access_token': create_access_token(identity=self.id),
            'refresh_token': create_refresh_token(identity=self.id)
        }

    def __repr__(self) -> str:
        return f'<User {self.email}>'


class Institution(db.Model):
    """Multi-tenant institution (school, university, tutoring center)."""
    __tablename__ = 'institutions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(50))  # school, university, tutoring_center
    domain: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    branding: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    subscription_tier: Mapped[str] = mapped_column(String(20), default='free')
    subscription_expires: Mapped[Optional[datetime]] = mapped_column(DateTime)
    features: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    settings: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    departments: Mapped[List['Department']] = relationship(back_populates='institution', cascade='all, delete-orphan')
    courses: Mapped[List['Course']] = relationship(back_populates='institution', cascade='all, delete-orphan')
    users: Mapped[List['UserRole']] = relationship(back_populates='institution')
    resources: Mapped[List['Resource']] = relationship(back_populates='institution')
    announcements: Mapped[List['Announcement']] = relationship(back_populates='institution')
    integrations: Mapped[List['Integration']] = relationship(back_populates='institution')
    payments: Mapped[List['Payment']] = relationship(back_populates='institution')
    feature_flags: Mapped[List['FeatureFlag']] = relationship(back_populates='institution', cascade='all, delete-orphan')

    # New relationships
    programmes: Mapped[List['Programme']] = relationship(back_populates='institution', cascade='all, delete-orphan')
    hostels: Mapped[List['Hostel']] = relationship(back_populates='institution', cascade='all, delete-orphan')
    library_resources: Mapped[List['LibraryResource']] = relationship(back_populates='institution', cascade='all, delete-orphan')
    academic_calendars: Mapped[List['AcademicCalendar']] = relationship(back_populates='institution', cascade='all, delete-orphan')
    policies: Mapped[List['Policy']] = relationship(back_populates='institution', cascade='all, delete-orphan')
    admission_applications: Mapped[List['AdmissionApplication']] = relationship(back_populates='institution', cascade='all, delete-orphan')
    exam_timetables: Mapped[List['ExamTimetable']] = relationship(back_populates='institution', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Institution {self.name}>'


class Role(db.Model):
    """Roles with associated permissions."""
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    permissions: Mapped[List[str]] = mapped_column(JSONB, default=[])  # list of permission strings
    institution_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=True)  # Nullable for global roles

    def __repr__(self) -> str:
        return f'<Role {self.name}>'


class UserRole(db.Model):
    """Many-to-many association between users, institutions, and roles."""
    __tablename__ = 'user_roles'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, ForeignKey('roles.id'), nullable=False)
    context: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})  # e.g., department_id
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped['User'] = relationship(back_populates='roles')
    institution: Mapped['Institution'] = relationship(back_populates='users')
    role: Mapped['Role'] = relationship()

    __table_args__ = (
        UniqueConstraint('user_id', 'institution_id', 'role_id', name='unique_user_institution_role'),
    )

    def __repr__(self) -> str:
        return f'<UserRole user={self.user_id} inst={self.institution_id} role={self.role_id}>'


class Department(db.Model):
    __tablename__ = 'departments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('departments.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='departments')
    parent: Mapped['Department'] = relationship(remote_side=[id], backref='children')
    courses: Mapped[List['Course']] = relationship(back_populates='department')

    def __repr__(self) -> str:
        return f'<Department {self.name}>'


class Course(db.Model):
    __tablename__ = 'courses'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=False)
    department_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('departments.id'))
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    credits: Mapped[int] = mapped_column(Integer, default=3)
    syllabus: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    status: Mapped[str] = mapped_column(String(20), default='active')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # New fields for approval workflow
    submitted_for_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_notes: Mapped[Optional[str]] = mapped_column(Text)
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rejected_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='courses')
    department: Mapped['Department'] = relationship(back_populates='courses')
    offerings: Mapped[List['CourseOffering']] = relationship(back_populates='course', cascade='all, delete-orphan')
    prerequisites: Mapped[List['Course']] = relationship(
        secondary=course_prerequisites,
        primaryjoin=id == course_prerequisites.c.course_id,
        secondaryjoin=id == course_prerequisites.c.prerequisite_id,
        backref='dependent_courses'
    )
    approved_by_user: Mapped['User'] = relationship(foreign_keys=[approved_by])
    rejected_by_user: Mapped['User'] = relationship(foreign_keys=[rejected_by])

    __table_args__ = (
        UniqueConstraint('institution_id', 'code', name='unique_institution_course_code'),
    )

    def __repr__(self) -> str:
        return f'<Course {self.code}>'


class CourseOffering(db.Model):
    __tablename__ = 'course_offerings'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey('courses.id'), nullable=False)
    term: Mapped[Optional[str]] = mapped_column(String(20))
    year: Mapped[Optional[int]] = mapped_column(Integer)
    instructor_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))
    schedule: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    room: Mapped[Optional[str]] = mapped_column(String(50))
    capacity: Mapped[int] = mapped_column(Integer, default=30)
    status: Mapped[str] = mapped_column(String(20), default='active')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    course: Mapped['Course'] = relationship(back_populates='offerings')
    instructor: Mapped['User'] = relationship(back_populates='taught_courses')
    enrollments: Mapped[List['Enrollment']] = relationship(back_populates='course_offering', cascade='all, delete-orphan')
    assignments: Mapped[List['Assignment']] = relationship(back_populates='course_offering', cascade='all, delete-orphan')
    attendance_records: Mapped[List['Attendance']] = relationship(back_populates='course_offering', cascade='all, delete-orphan')
    assignment_groups: Mapped[List['AssignmentGroup']] = relationship(back_populates='course_offering', cascade='all, delete-orphan')
    waitlist: Mapped[List['Waitlist']] = relationship(back_populates='course_offering', cascade='all, delete-orphan')
    resources: Mapped[List['Resource']] = relationship(back_populates='course_offering')
    live_sessions: Mapped[List['LiveSession']] = relationship(back_populates='course_offering', cascade='all, delete-orphan')
    exam_timetables: Mapped[List['ExamTimetable']] = relationship(back_populates='course_offering', cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint('course_id', 'term', 'year', name='unique_course_offering'),
    )

    @property
    def enrolled_count(self) -> int:
        """Current number of enrolled students."""
        return len([e for e in self.enrollments if e.status == 'enrolled'])

    @property
    def available_seats(self) -> int:
        return self.capacity - self.enrolled_count

    def __repr__(self) -> str:
        return f'<Offering {self.course.code} {self.term} {self.year}>'


class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    course_offering_id: Mapped[int] = mapped_column(Integer, ForeignKey('course_offerings.id'), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='enrolled')
    enrollment_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    grade: Mapped[Optional[float]] = mapped_column(Float)
    letter_grade: Mapped[Optional[str]] = mapped_column(String(2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    student: Mapped['User'] = relationship(back_populates='enrollments')
    course_offering: Mapped['CourseOffering'] = relationship(back_populates='enrollments')
    grades: Mapped[List['Grade']] = relationship(back_populates='enrollment', cascade='all, delete-orphan')

    __table_args__ = (
        UniqueConstraint('user_id', 'course_offering_id', name='unique_enrollment'),
    )

    def __repr__(self) -> str:
        return f'<Enrollment {self.user_id} in {self.course_offering_id}>'


class AssignmentGroup(db.Model):
    __tablename__ = 'assignment_groups'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_offering_id: Mapped[int] = mapped_column(Integer, ForeignKey('course_offerings.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    drop_lowest: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    course_offering: Mapped['CourseOffering'] = relationship(back_populates='assignment_groups')
    assignments: Mapped[List['Assignment']] = relationship(back_populates='group', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<AssignmentGroup {self.name}>'


class Assignment(db.Model):
    __tablename__ = 'assignments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_offering_id: Mapped[int] = mapped_column(Integer, ForeignKey('course_offerings.id'), nullable=False)
    group_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('assignment_groups.id'))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    points_possible: Mapped[float] = mapped_column(Float, default=100.0)
    rubric: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    submission_type: Mapped[str] = mapped_column(String(20), default='file')
    allowed_file_types: Mapped[List[str]] = mapped_column(JSONB, default=[])
    max_file_size: Mapped[int] = mapped_column(Integer, default=10485760)
    late_policy: Mapped[str] = mapped_column(String(20), default='not_allowed')
    late_penalty: Mapped[float] = mapped_column(Float, default=0.10)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # New fields for exams
    is_exam: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    proctoring_required: Mapped[bool] = mapped_column(Boolean, default=False)
    questions: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)  # stores exam structure

    # Relationships
    course_offering: Mapped['CourseOffering'] = relationship(back_populates='assignments')
    group: Mapped['AssignmentGroup'] = relationship(back_populates='assignments')
    submissions: Mapped[List['Submission']] = relationship(back_populates='assignment', cascade='all, delete-orphan')
    exam_sessions: Mapped[List['ExamSession']] = relationship(back_populates='exam', cascade='all, delete-orphan')
    proctoring_logs: Mapped[List['ProctoringLog']] = relationship(back_populates='exam', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Assignment {self.title}>'


class Submission(db.Model):
    __tablename__ = 'submissions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assignment_id: Mapped[int] = mapped_column(Integer, ForeignKey('assignments.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    file_url: Mapped[Optional[str]] = mapped_column(String(500))
    text: Mapped[Optional[str]] = mapped_column(Text)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    grade: Mapped[Optional[float]] = mapped_column(Float)
    feedback: Mapped[Optional[str]] = mapped_column(Text)
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default='submitted')

    # Relationships
    assignment: Mapped['Assignment'] = relationship(back_populates='submissions')
    student: Mapped['User'] = relationship(back_populates='submissions')

    __table_args__ = (
        UniqueConstraint('assignment_id', 'user_id', name='unique_submission'),
    )

    def __repr__(self) -> str:
        return f'<Submission {self.id}>'


class Grade(db.Model):
    __tablename__ = 'grades'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(Integer, ForeignKey('enrollments.id'), nullable=False)
    assignment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('assignments.id'))
    points_earned: Mapped[Optional[float]] = mapped_column(Float)
    percentage: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    enrollment: Mapped['Enrollment'] = relationship(back_populates='grades')
    assignment: Mapped['Assignment'] = relationship()


class Attendance(db.Model):
    __tablename__ = 'attendance'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_offering_id: Mapped[int] = mapped_column(Integer, ForeignKey('course_offerings.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='present')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    course_offering: Mapped['CourseOffering'] = relationship(back_populates='attendance_records')
    student: Mapped['User'] = relationship()

    __table_args__ = (
        UniqueConstraint('course_offering_id', 'user_id', 'date', name='unique_attendance'),
    )


class Waitlist(db.Model):
    __tablename__ = 'waitlist'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_offering_id: Mapped[int] = mapped_column(Integer, ForeignKey('course_offerings.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    course_offering: Mapped['CourseOffering'] = relationship(back_populates='waitlist')
    user: Mapped['User'] = relationship()

    __table_args__ = (
        UniqueConstraint('course_offering_id', 'user_id', name='unique_waitlist'),
    )


class Announcement(db.Model):
    __tablename__ = 'announcements'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=False)
    course_offering_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('course_offerings.id'))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default='normal')
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, onupdate=datetime.utcnow)

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='announcements')
    course_offering: Mapped['CourseOffering'] = relationship()
    author: Mapped['User'] = relationship(foreign_keys=[created_by])


class Message(db.Model):
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sender_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    recipient_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    subject: Mapped[Optional[str]] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    sender: Mapped['User'] = relationship(foreign_keys=[sender_id], back_populates='messages_sent')
    recipient: Mapped['User'] = relationship(foreign_keys=[recipient_id], back_populates='messages_received')


class Notification(db.Model):
    __tablename__ = 'notifications'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    type: Mapped[str] = mapped_column(String(50))
    title: Mapped[Optional[str]] = mapped_column(String(200))
    message: Mapped[Optional[str]] = mapped_column(Text)
    data: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped['User'] = relationship(back_populates='notifications')


class Resource(db.Model):
    __tablename__ = 'resources'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=False)
    course_offering_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('course_offerings.id'))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(50))
    url: Mapped[Optional[str]] = mapped_column(String(500))
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    visibility: Mapped[str] = mapped_column(String(20), default='institution')
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='resources')
    course_offering: Mapped['CourseOffering'] = relationship(back_populates='resources')
    author: Mapped['User'] = relationship()


class Integration(db.Model):
    __tablename__ = 'integrations'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='integrations')


class Payment(db.Model):
    __tablename__ = 'payments'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10,2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default='USD')
    status: Mapped[str] = mapped_column(String(20), default='pending')
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(100))
    paystack_reference: Mapped[Optional[str]] = mapped_column(String(100))  # For Paystack
    description: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped['User'] = relationship(back_populates='payments')
    institution: Mapped['Institution'] = relationship(back_populates='payments')


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    table_name: Mapped[Optional[str]] = mapped_column(String(50))
    record_id: Mapped[Optional[int]] = mapped_column(Integer)
    changes: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped['User'] = relationship(back_populates='audit_logs')


class FeatureFlag(db.Model):
    __tablename__ = 'feature_flags'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('institutions.id'))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='feature_flags')


class GDPRConsent(db.Model):
    """Tracks user consent for GDPR purposes."""
    __tablename__ = 'gdpr_consent'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    consent_type: Mapped[str] = mapped_column(String(50))  # marketing, analytics, etc.
    given: Mapped[bool] = mapped_column(Boolean, default=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    user: Mapped['User'] = relationship(back_populates='consent_records')


# ==================== NEW MODELS (appended) ====================

class LiveSession(db.Model):
    """Live class session using Jitsi or similar."""
    __tablename__ = 'live_sessions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_offering_id: Mapped[int] = mapped_column(Integer, ForeignKey('course_offerings.id'), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    meeting_url: Mapped[Optional[str]] = mapped_column(String(500))
    recording_url: Mapped[Optional[str]] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default='scheduled')
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    course_offering: Mapped['CourseOffering'] = relationship(back_populates='live_sessions')
    creator: Mapped['User'] = relationship(foreign_keys=[created_by])
    attendance_sessions: Mapped[List['AttendanceSession']] = relationship(back_populates='live_session', cascade='all, delete-orphan')


class AttendanceSession(db.Model):
    __tablename__ = 'attendance_sessions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    live_session_id: Mapped[int] = mapped_column(Integer, ForeignKey('live_sessions.id'), nullable=False)
    join_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    leave_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    active_time: Mapped[int] = mapped_column(Integer, default=0)  # in seconds
    total_duration: Mapped[int] = mapped_column(Integer, default=0)  # computed on leave

    # Relationships
    user: Mapped['User'] = relationship(back_populates='attendance_sessions')
    live_session: Mapped['LiveSession'] = relationship(back_populates='attendance_sessions')


class ProctoringLog(db.Model):
    __tablename__ = 'proctoring_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey('assignments.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    event_type: Mapped[str] = mapped_column(String(50))
    screenshot_url: Mapped[Optional[str]] = mapped_column(String(500))
    metadata: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})

    # Relationships
    exam: Mapped['Assignment'] = relationship(back_populates='proctoring_logs')
    user: Mapped['User'] = relationship(back_populates='proctoring_logs')


class ExamSession(db.Model):
    __tablename__ = 'exam_sessions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(Integer, ForeignKey('assignments.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime)
    answers: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default='in_progress')
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)
    flag_reason: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    exam: Mapped['Assignment'] = relationship(back_populates='exam_sessions')
    user: Mapped['User'] = relationship(back_populates='exam_sessions')
    proctoring_logs: Mapped[List['ProctoringLog']] = relationship(backref='exam_session', cascade='all, delete-orphan')


class Policy(db.Model):
    __tablename__ = 'policies'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='policies')
    acceptances: Mapped[List['UserPolicyAcceptance']] = relationship(back_populates='policy', cascade='all, delete-orphan')


class UserPolicyAcceptance(db.Model):
    __tablename__ = 'user_policy_acceptance'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    policy_id: Mapped[int] = mapped_column(Integer, ForeignKey('policies.id'), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(200))

    # Relationships
    user: Mapped['User'] = relationship(back_populates='policy_acceptances')
    policy: Mapped['Policy'] = relationship(back_populates='acceptances')


class Programme(db.Model):
    __tablename__ = 'programmes'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(20))
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('departments.id'))
    duration_years: Mapped[int] = mapped_column(Integer)
    requirements: Mapped[Dict[str, Any]] = mapped_column(JSONB)

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='programmes')
    department: Mapped['Department'] = relationship()
    students: Mapped[List['User']] = relationship(back_populates='programme')
    requirements_detail: Mapped[List['ProgrammeRequirement']] = relationship(back_populates='programme', cascade='all, delete-orphan')


class ProgrammeRequirement(db.Model):
    __tablename__ = 'programme_requirements'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    programme_id: Mapped[int] = mapped_column(Integer, ForeignKey('programmes.id'))
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey('courses.id'))
    level: Mapped[int] = mapped_column(Integer)
    semester: Mapped[int] = mapped_column(Integer)
    is_core: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    programme: Mapped['Programme'] = relationship(back_populates='requirements_detail')
    course: Mapped['Course'] = relationship()


class AdmissionApplication(db.Model):
    __tablename__ = 'admission_applications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'))
    programme_id: Mapped[int] = mapped_column(Integer, ForeignKey('programmes.id'))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20))
    jamb_reg_no: Mapped[str] = mapped_column(String(20), unique=True)
    jamb_score: Mapped[int] = mapped_column(Integer)
    olevel_results: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    admitted_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))
    admitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='admission_applications')
    programme: Mapped['Programme'] = relationship()
    student: Mapped['User'] = relationship(foreign_keys=[admitted_by])


class SemesterRegistration(db.Model):
    __tablename__ = 'semester_registrations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    academic_session: Mapped[str] = mapped_column(String(20))
    semester: Mapped[str] = mapped_column(String(10))
    registration_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), default='draft')
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    student: Mapped['User'] = relationship(back_populates='registered_semesters')
    approver: Mapped['User'] = relationship(foreign_keys=[approved_by])
    registered_courses: Mapped[List['RegisteredCourse']] = relationship(back_populates='semester_registration', cascade='all, delete-orphan')


class RegisteredCourse(db.Model):
    __tablename__ = 'registered_courses'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semester_registration_id: Mapped[int] = mapped_column(Integer, ForeignKey('semester_registrations.id'))
    course_offering_id: Mapped[int] = mapped_column(Integer, ForeignKey('course_offerings.id'))
    status: Mapped[str] = mapped_column(String(20), default='registered')

    # Relationships
    semester_registration: Mapped['SemesterRegistration'] = relationship(back_populates='registered_courses')
    course_offering: Mapped['CourseOffering'] = relationship()


class ExamTimetable(db.Model):
    __tablename__ = 'exam_timetables'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'))
    course_offering_id: Mapped[int] = mapped_column(Integer, ForeignKey('course_offerings.id'))
    exam_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    venue: Mapped[str] = mapped_column(String(100))
    invigilators: Mapped[List[int]] = mapped_column(JSONB)  # list of user IDs

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='exam_timetables')
    course_offering: Mapped['CourseOffering'] = relationship(back_populates='exam_timetables')
    attendances: Mapped[List['ExamAttendance']] = relationship(back_populates='exam_timetable', cascade='all, delete-orphan')


class ExamAttendance(db.Model):
    __tablename__ = 'exam_attendance'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_timetable_id: Mapped[int] = mapped_column(Integer, ForeignKey('exam_timetables.id'))
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    signed_in: Mapped[bool] = mapped_column(Boolean, default=False)
    signed_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    exam_timetable: Mapped['ExamTimetable'] = relationship(back_populates='attendances')
    student: Mapped['User'] = relationship(back_populates='exam_attendances')


class Hostel(db.Model):
    __tablename__ = 'hostels'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'))
    name: Mapped[str] = mapped_column(String(100))
    gender: Mapped[str] = mapped_column(String(10))
    total_rooms: Mapped[int] = mapped_column(Integer)
    warden_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='hostels')
    warden: Mapped['User'] = relationship()
    rooms: Mapped[List['Room']] = relationship(back_populates='hostel', cascade='all, delete-orphan')
    applications: Mapped[List['HostelApplication']] = relationship(back_populates='hostel', cascade='all, delete-orphan')


class Room(db.Model):
    __tablename__ = 'rooms'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hostel_id: Mapped[int] = mapped_column(Integer, ForeignKey('hostels.id'))
    room_number: Mapped[str] = mapped_column(String(20))
    capacity: Mapped[int] = mapped_column(Integer)

    # Relationships
    hostel: Mapped['Hostel'] = relationship(back_populates='rooms')
    occupancies: Mapped[List['RoomOccupancy']] = relationship(back_populates='room', cascade='all, delete-orphan')


class RoomOccupancy(db.Model):
    __tablename__ = 'room_occupancies'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(Integer, ForeignKey('rooms.id'))
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    allocated_from: Mapped[date] = mapped_column(Date)
    allocated_to: Mapped[Optional[date]] = mapped_column(Date)

    # Relationships
    room: Mapped['Room'] = relationship(back_populates='occupancies')
    student: Mapped['User'] = relationship(back_populates='room_occupancies')


class HostelApplication(db.Model):
    __tablename__ = 'hostel_applications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hostel_id: Mapped[int] = mapped_column(Integer, ForeignKey('hostels.id'))
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    application_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    preferred_room_type: Mapped[Optional[str]] = mapped_column(String(50))

    # Relationships
    hostel: Mapped['Hostel'] = relationship(back_populates='applications')
    student: Mapped['User'] = relationship(back_populates='hostel_applications')


class LibraryResource(db.Model):
    __tablename__ = 'library_resources'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'))
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(100))
    isbn: Mapped[Optional[str]] = mapped_column(String(20))
    resource_type: Mapped[str] = mapped_column(String(50))
    location: Mapped[str] = mapped_column(String(100))
    copies_total: Mapped[int] = mapped_column(Integer)
    copies_available: Mapped[int] = mapped_column(Integer)

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='library_resources')
    borrowing_records: Mapped[List['BorrowingRecord']] = relationship(back_populates='resource', cascade='all, delete-orphan')


class BorrowingRecord(db.Model):
    __tablename__ = 'borrowing_records'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'))
    resource_id: Mapped[int] = mapped_column(Integer, ForeignKey('library_resources.id'))
    borrowed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    due_date: Mapped[date] = mapped_column(Date)
    returned_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    fine: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    user: Mapped['User'] = relationship(back_populates='borrowing_records')
    resource: Mapped['LibraryResource'] = relationship(back_populates='borrowing_records')


class StaffProfile(db.Model):
    __tablename__ = 'staff_profiles'
    id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(50), unique=True)
    department_id: Mapped[int] = mapped_column(Integer, ForeignKey('departments.id'))
    position: Mapped[str] = mapped_column(String(100))
    date_employed: Mapped[date] = mapped_column(Date)
    salary_grade: Mapped[str] = mapped_column(String(20))
    bank_details: Mapped[Dict[str, Any]] = mapped_column(JSONB)

    # Relationships
    user: Mapped['User'] = relationship(back_populates='staff_profile')
    department: Mapped['Department'] = relationship()
    leave_applications: Mapped[List['LeaveApplication']] = relationship(back_populates='staff', cascade='all, delete-orphan')


class LeaveApplication(db.Model):
    __tablename__ = 'leave_applications'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    staff_id: Mapped[int] = mapped_column(Integer, ForeignKey('staff_profiles.id'))
    leave_type: Mapped[str] = mapped_column(String(50))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    approved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id'))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    staff: Mapped['StaffProfile'] = relationship(back_populates='leave_applications')
    approver: Mapped['User'] = relationship(foreign_keys=[approved_by])


class Alumni(db.Model):
    __tablename__ = 'alumni'
    id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), primary_key=True)
    graduation_year: Mapped[int] = mapped_column(Integer)
    current_employer: Mapped[Optional[str]] = mapped_column(String(200))
    occupation: Mapped[Optional[str]] = mapped_column(String(100))
    contact_email: Mapped[str] = mapped_column(String(120))
    newsletter_opt_in: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    user: Mapped['User'] = relationship(back_populates='alumni_profile')


class AcademicCalendar(db.Model):
    __tablename__ = 'academic_calendar'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'))
    session: Mapped[str] = mapped_column(String(20))
    semester: Mapped[str] = mapped_column(String(10))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    activities: Mapped[Dict[str, Any]] = mapped_column(JSONB)

    # Relationships
    institution: Mapped['Institution'] = relationship(back_populates='academic_calendars')


# Indexes for performance
Index('idx_enrollment_user', Enrollment.user_id)
Index('idx_enrollment_offering', Enrollment.course_offering_id)
Index('idx_assignment_offering', Assignment.course_offering_id)
Index('idx_submission_assignment', Submission.assignment_id)
Index('idx_submission_user', Submission.user_id)
Index('idx_attendance_offering', Attendance.course_offering_id)
Index('idx_attendance_user', Attendance.user_id)
Index('idx_notification_user_read', Notification.user_id, Notification.read)
Index('idx_auditlog_user', AuditLog.user_id)
Index('idx_auditlog_created', AuditLog.created_at)
Index('idx_gdpr_user', GDPRConsent.user_id)
Index('idx_live_session_offering', LiveSession.course_offering_id)
Index('idx_attendance_session_user', AttendanceSession.user_id)
Index('idx_exam_session_user', ExamSession.user_id)
Index('idx_proctoring_log_user', ProctoringLog.user_id)
Index('idx_registered_course_reg', RegisteredCourse.semester_registration_id)
Index('idx_borrowing_user', BorrowingRecord.user_id)
Index('idx_leave_staff', LeaveApplication.staff_id)
