"""
Run Alembic upgrade programmatically for convenience on devices where alembic CLI may not be available.
Usage: python -m financial.scripts.run_alembic_upgrade
"""
from alembic.config import Config
from alembic import command
import os

def run_upgrade():
    cfg = Config(os.path.join(os.path.dirname(__file__), '..', '..', 'alembic.ini'))
    # allow overriding DB URL via env
    db = os.getenv('DATABASE_URL')
    if db:
        cfg.set_main_option('sqlalchemy.url', db)
    command.upgrade(cfg, 'head')

if __name__ == '__main__':
    run_upgrade()
