"""Database module for AI Brain - imports from shared.db for consistency."""
from shared.db import get_engine, get_session  # noqa: F401


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

