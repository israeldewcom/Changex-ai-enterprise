import click
from flask.cli import with_appcontext
from app import db
from app.models import User, Institution, Role, UserRole, Course, Department, CourseOffering, Enrollment, Assignment, AssignmentGroup
from faker import Faker
from werkzeug.security import generate_password_hash
import random

fake = Faker()

@click.command('seed-db')
@with_appcontext
def seed_db():
    """Seed database with fake data."""
    # ... (same as original but enhanced with type hints and more data)
