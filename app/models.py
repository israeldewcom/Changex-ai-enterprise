"""
Database models for ChangeX Eduspace.
Includes multi-tenancy, RBAC, and core educational entities.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, 
    Table, Text, Float, Numeric, Index, CheckConstraint, UniqueConstraint
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

    # Relationships
    roles: Mapped[List[UserRole]] = relationship(back_populates='user', cascade='all, delete-orphan')
    enrollments: Mapped[List[Enrollment]] = relationship(back_populates='student', cascade='all, delete-orphan')
    submissions: Mapped[List[Submission]] = relationship(back_populates='student', cascade='all, delete-orphan')
    taught_courses: Mapped[List[CourseOffering]] = relationship(back_populates='instructor')
    messages_sent: Mapped[List[Message]] = relationship(foreign_keys='Message.sender_id', back_populates='sender')
    messages_received: Mapped[List[Message]] = relationship(foreign_keys='Message.recipient_id', back_populates='recipient')
    notifications: Mapped[List[Notification]] = relationship(back_populates='user', cascade='all, delete-orphan')
    payments: Mapped[List[Payment]] = relationship(back_populates='user')
    audit_logs: Mapped[List[AuditLog]] = relationship(back_populates='user')
    consent_records: Mapped[List[GDPRConsent]] = relationship(back_populates='user', cascade='all, delete-orphan')

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
    departments: Mapped[List[Department]] = relationship(back_populates='institution', cascade='all, delete-orphan')
    courses: Mapped[List[Course]] = relationship(back_populates='institution', cascade='all, delete-orphan')
    users: Mapped[List[UserRole]] = relationship(back_populates='institution')
    resources: Mapped[List[Resource]] = relationship(back_populates='institution')
    announcements: Mapped[List[Announcement]] = relationship(back_populates='institution')
    integrations: Mapped[List[Integration]] = relationship(back_populates='institution')
    payments: Mapped[List[Payment]] = relationship(back_populates='institution')
    feature_flags: Mapped[List[FeatureFlag]] = relationship(back_populates='institution', cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f'<Institution {self.name}>'

class Role(db.Model):
    """Roles with associated permissions."""
    __tablename__ = 'roles'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    permissions: Mapped[List[str]] = mapped_column(JSONB, default=[])  # list of permission strings

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
    user: Mapped[User] = relationship(back_populates='roles')
    institution: Mapped[Institution] = relationship(back_populates='users')
    role: Mapped[Role] = relationship()

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
    institution: Mapped[Institution] = relationship(back_populates='departments')
    parent: Mapped[Department] = relationship(remote_side=[id], backref='children')
    courses: Mapped[List[Course]] = relationship(back_populates='department')

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

    # Relationships
    institution: Mapped[Institution] = relationship(back_populates='courses')
    department: Mapped[Department] = relationship(back_populates='courses')
    offerings: Mapped[List[CourseOffering]] = relationship(back_populates='course', cascade='all, delete-orphan')
    prerequisites: Mapped[List[Course]] = relationship(
        secondary=course_prerequisites,
        primaryjoin=id == course_prerequisites.c.course_id,
        secondaryjoin=id == course_prerequisites.c.prerequisite_id,
        backref='dependent_courses'
    )

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
    course: Mapped[Course] = relationship(back_populates='offerings')
    instructor: Mapped[User] = relationship(back_populates='taught_courses')
    enrollments: Mapped[List[Enrollment]] = relationship(back_populates='course_offering', cascade='all, delete-orphan')
    assignments: Mapped[List[Assignment]] = relationship(back_populates='course_offering', cascade='all, delete-orphan')
    attendance_records: Mapped[List[Attendance]] = relationship(back_populates='course_offering', cascade='all, delete-orphan')
    assignment_groups: Mapped[List[AssignmentGroup]] = relationship(back_populates='course_offering', cascade='all, delete-orphan')
    waitlist: Mapped[List[Waitlist]] = relationship(back_populates='course_offering', cascade='all, delete-orphan')
    resources: Mapped[List[Resource]] = relationship(back_populates='course_offering')

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
    student: Mapped[User] = relationship(back_populates='enrollments')
    course_offering: Mapped[CourseOffering] = relationship(back_populates='enrollments')
    grades: Mapped[List[Grade]] = relationship(back_populates='enrollment', cascade='all, delete-orphan')

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
    course_offering: Mapped[CourseOffering] = relationship(back_populates='assignment_groups')
    assignments: Mapped[List[Assignment]] = relationship(back_populates='group', cascade='all, delete-orphan')

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

    # Relationships
    course_offering: Mapped[CourseOffering] = relationship(back_populates='assignments')
    group: Mapped[AssignmentGroup] = relationship(back_populates='assignments')
    submissions: Mapped[List[Submission]] = relationship(back_populates='assignment', cascade='all, delete-orphan')

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
    assignment: Mapped[Assignment] = relationship(back_populates='submissions')
    student: Mapped[User] = relationship(back_populates='submissions')

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
    enrollment: Mapped[Enrollment] = relationship(back_populates='grades')
    assignment: Mapped[Assignment] = relationship()

class Attendance(db.Model):
    __tablename__ = 'attendance'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_offering_id: Mapped[int] = mapped_column(Integer, ForeignKey('course_offerings.id'), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default='present')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    course_offering: Mapped[CourseOffering] = relationship(back_populates='attendance_records')
    student: Mapped[User] = relationship()

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
    course_offering: Mapped[CourseOffering] = relationship(back_populates='waitlist')
    user: Mapped[User] = relationship()

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
    institution: Mapped[Institution] = relationship(back_populates='announcements')
    course_offering: Mapped[CourseOffering] = relationship()
    author: Mapped[User] = relationship(foreign_keys=[created_by])

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
    sender: Mapped[User] = relationship(foreign_keys=[sender_id], back_populates='messages_sent')
    recipient: Mapped[User] = relationship(foreign_keys=[recipient_id], back_populates='messages_received')

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
    user: Mapped[User] = relationship(back_populates='notifications')

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
    institution: Mapped[Institution] = relationship(back_populates='resources')
    course_offering: Mapped[CourseOffering] = relationship(back_populates='resources')
    author: Mapped[User] = relationship()

class Integration(db.Model):
    __tablename__ = 'integrations'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    config: Mapped[Dict[str, Any]] = mapped_column(JSONB, default={})
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    institution: Mapped[Institution] = relationship(back_populates='integrations')

class Payment(db.Model):
    __tablename__ = 'payments'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    institution_id: Mapped[int] = mapped_column(Integer, ForeignKey('institutions.id'), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10,2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default='USD')
    status: Mapped[str] = mapped_column(String(20), default='pending')
    stripe_payment_intent_id: Mapped[Optional[str]] = mapped_column(String(100))
    description: Mapped[Optional[str]] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped[User] = relationship(back_populates='payments')
    institution: Mapped[Institution] = relationship(back_populates='payments')

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
    user: Mapped[User] = relationship(back_populates='audit_logs')

class FeatureFlag(db.Model):
    __tablename__ = 'feature_flags'
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    institution_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('institutions.id'))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    institution: Mapped[Institution] = relationship(back_populates='feature_flags')

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
    user: Mapped[User] = relationship(back_populates='consent_records')

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
