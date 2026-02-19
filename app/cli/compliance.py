import click
from flask.cli import with_appcontext
from app import db
from app.models import User
from app.utils.compliance import anonymize_user
from datetime import datetime, timedelta

@click.command('anonymize-old-users')
@with_appcontext
def anonymize_old_users():
    """Anonymize users who have been inactive for longer than retention period."""
    from config import Config
    days = Config.DATA_RETENTION_DAYS
    cutoff = datetime.utcnow() - timedelta(days=days)
    users = User.query.filter(User.last_login < cutoff).all()
    for user in users:
        anonymize_user(user.id)
    click.echo(f"Anonymized {len(users)} users")
