import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool


def _prefer_memory():
    # Prefer in-memory DB when running under pytest or when /data is not writable
    if any('pytest' in (arg or '') for arg in sys.argv) or 'PYTEST_CURRENT_TEST' in os.environ:
        return True
    if not (os.path.exists('/data') and os.access('/data', os.W_OK)):
        return True
    return False


_engine_cache = {}


def get_engine(env_var_name: str, fallback_db_url: str):
    """Return a SQLAlchemy engine using the environment var if set, otherwise a sensible default.

    - If the environment variable is set, its value is used as DB URL.
    - If running under pytest or /data is not writable, an in-memory SQLite DB is used.
    - Engines are cached by URL so multiple modules requesting the same URL (notably
      the shared in-memory URL used in tests) receive the same Engine instance.
    """
    db_url = os.getenv(env_var_name)
    if db_url:
        url = db_url
    else:
        if _prefer_memory():
            url = 'sqlite:///:memory:'
        else:
            url = fallback_db_url

    # Return a cached engine for the same URL so in-memory DB is shared across modules
    if url in _engine_cache:
        return _engine_cache[url]

    if url == 'sqlite:///:memory:':
        # Use StaticPool so the same in-memory DB is accessible across sessions and threads
        engine = create_engine(url, echo=False, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        engine = create_engine(url, echo=False)

    _engine_cache[url] = engine
    return engine


def get_session():
    """Return a SQLModel-backed session for the AI Brain database (supports .exec())."""
    from sqlmodel import Session as SQLModelSession
    engine = get_engine('AI_BRAIN_DB_URL', 'sqlite:////data/ai_brain.db')
    return SQLModelSession(engine)


def init_db(env_var_name: str = 'AI_BRAIN_DB_URL', fallback_db_url: str = 'sqlite:////data/ai_brain.db') -> None:
    """Create database tables for the AI Brain service using SQLModel metadata.

    This is intended to be called on application startup (or during tests) so
    that the shared models have their tables created in the configured engine.
    """
    try:
        # Ensure model modules are imported so SQLModel.metadata includes their tables
        try:
            import shared.models
        except Exception:
            pass
        try:
            import ai_brain.models
        except Exception:
            pass
        from sqlmodel import SQLModel
        engine = get_engine(env_var_name, fallback_db_url)
        SQLModel.metadata.create_all(engine)
    except Exception:
        # Fail silently during import-time checks; errors will be logged elsewhere
        pass
