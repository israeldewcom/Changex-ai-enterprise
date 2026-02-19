# app/cli/__init__.py
import click
from flask.cli import with_appcontext
from .seed import seed_db
from .backup import backup_db
from .compliance import anonymize_old_users

def register_commands(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(seed_db)
    app.cli.add_command(backup_db)
    app.cli.add_command(anonymize_old_users)
