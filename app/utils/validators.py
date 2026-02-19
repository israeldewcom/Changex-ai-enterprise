"""
Input validation using Marshmallow schemas and custom validators.
"""
import re
from typing import Any, Dict
from marshmallow import Schema, fields, validate, ValidationError, post_load
from datetime import datetime

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> bool:
    """
    Validate password strength:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    """
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

def validate_phone(phone: str) -> bool:
    """Basic international phone validation."""
    pattern = r'^\+?[1-9]\d{1,14}$'
    return re.match(pattern, phone) is not None

# Marshmallow schemas
class UserRegistrationSchema(Schema):
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    full_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    accept_terms = fields.Bool(required=True, validate=validate.Equal(True))

    @post_load
    def validate_password_strength(self, data: Dict, **kwargs) -> Dict:
        if not validate_password(data['password']):
            raise ValidationError('Password must contain at least 8 chars, one uppercase, one lowercase, and one number')
        return data

class InstitutionCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    type = fields.Str(required=True, validate=validate.OneOf(['school', 'university', 'tutoring_center']))
    domain = fields.Str(allow_none=True)
    branding = fields.Dict(allow_none=True)
    subscription_tier = fields.Str(validate=validate.OneOf(['free', 'pro', 'enterprise']), missing='free')

class CourseCreateSchema(Schema):
    institution_id = fields.Int(required=True)
    department_id = fields.Int(allow_none=True)
    code = fields.Str(required=True, validate=validate.Length(min=1, max=20))
    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    description = fields.Str(allow_none=True)
    credits = fields.Int(missing=3, validate=validate.Range(min=0, max=20))
    syllabus = fields.Dict(allow_none=True)

class AssignmentCreateSchema(Schema):
    course_offering_id = fields.Int(required=True)
    group_id = fields.Int(allow_none=True)
    title = fields.Str(required=True)
    description = fields.Str(allow_none=True)
    due_date = fields.DateTime(required=True)
    points_possible = fields.Float(missing=100.0)
    submission_type = fields.Str(missing='file', validate=validate.OneOf(['file', 'text', 'url']))
    allowed_file_types = fields.List(fields.Str(), missing=[])
    max_file_size = fields.Int(missing=10485760)
    late_policy = fields.Str(missing='not_allowed', validate=validate.OneOf(['not_allowed', 'allowed_with_penalty', 'allowed']))
    late_penalty = fields.Float(missing=0.10, validate=validate.Range(min=0, max=1))
