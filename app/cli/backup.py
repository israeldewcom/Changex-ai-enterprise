import click
from flask.cli import with_appcontext
import subprocess
import os
from datetime import datetime

@click.command('backup-db')
@with_appcontext
def backup_db():
    """Backup database to file."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        click.echo('DATABASE_URL not set')
        return
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"backup_{timestamp}.sql"
    cmd = f"pg_dump {db_url} > {filename}"
    subprocess.run(cmd, shell=True, check=True)
    click.echo(f"Backup saved to {filename}")
