"""
Database configuration for Reminder service
"""
import os
from sqlmodel import create_engine
from sqlalchemy.pool import StaticPool


def get_engine(env_var: str, default_url: str):
    """
    Get database engine with environment variable override support.

    Args:
        env_var: Environment variable name to check for custom DB URL
        default_url: Default database URL if env var not set

    Returns:
        SQLModel engine instance
    """
    db_url = os.getenv(env_var, default_url)

    # Use StaticPool for SQLite to allow sharing across threads
    if db_url.startswith('sqlite'):
        return create_engine(
            db_url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
    else:
        return create_engine(db_url, echo=False)
