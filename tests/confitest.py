import pytest
from app import create_app, db as _db
from app.models import User, Role, Institution
from config import TestingConfig

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def db(app):
    return _db

@pytest.fixture
def admin_user(db):
    role = Role(name='admin', permissions=['*'])
    db.session.add(role)
    user = User(email='admin@test.com', full_name='Admin')
    user.password = 'Admin123!'
    db.session.add(user)
    db.session.commit()
    return user
