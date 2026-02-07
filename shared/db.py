"""
Kilo Guardian - Unified Database Module (SQLAlchemy + SQLModel)

Single source of truth for all database engine creation.
Every service should import from here instead of having its own db.py.
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

_engine_cache = {}


def _prefer_memory() -> bool:
    """Use in-memory SQLite when running tests or when /data isn't writable."""
    if any("pytest" in (arg or "") for arg in sys.argv) or "PYTEST_CURRENT_TEST" in os.environ:
        return True
    if not (os.path.exists("/data") and os.access("/data", os.W_OK)):
        return True
    return False


def get_engine(env_var_name: str, fallback_db_url: str):
    """
    Return a SQLAlchemy engine, cached by URL.
    
    - Checks env var first
    - Falls back to in-memory SQLite during tests
    - Uses StaticPool for SQLite thread safety
    """
    db_url = os.getenv(env_var_name)
    if db_url:
        url = db_url
    elif _prefer_memory():
        url = "sqlite:///:memory:"
    else:
        url = fallback_db_url

    if url in _engine_cache:
        return _engine_cache[url]

    if url.startswith("sqlite"):
        engine = create_engine(
            url,
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        engine = create_engine(url, echo=False)

    _engine_cache[url] = engine
    return engine


def get_session(env_var_name: str = "DATABASE_URL", fallback_db_url: str = "sqlite:////data/kilo.db"):
    """Return a SQLModel Session for the given database."""
    from sqlmodel import Session as SQLModelSession
    engine = get_engine(env_var_name, fallback_db_url)
    return SQLModelSession(engine)
