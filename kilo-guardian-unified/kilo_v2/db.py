"""
Database helper for SQLAlchemy engine and session management.

This keeps runtime code using the existing sqlite3 calls for now,
but provides a central place to create a SQLAlchemy engine for
future migration and ORM usage.
"""

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from kilo_v2.config import ENVIRONMENT

_SessionLocal = None

_engine: Optional[Engine] = None
_engine_url: Optional[str] = None


def get_db_url() -> str:
    """Return DB URL. Default to sqlite at repo root for compatibility."""
    # Use explicit DATABASE_URL environment variable if provided
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    # Default to Postgres in production; otherwise, use SQLite for local dev/test convenience
    if ENVIRONMENT.lower() in ("production", "prod"):
        return "postgresql://postgres:postgres@localhost:5432/kilo_guardian"
    return "sqlite:///kilo_data/kilo_guardian.db"


def get_engine() -> Engine:
    global _engine
    global _engine_url
    url = get_db_url()
    # Recreate engine if DATABASE_URL changed since first creation
    if _engine is not None and _engine_url == url:
        return _engine

    # url already computed above
    # For SQLite URI, we need connect args for check_same_thread if used with SQLAlchemy
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    _engine = create_engine(url, connect_args=connect_args)
    _engine_url = url
    return _engine


def get_session_factory():
    global _SessionLocal
    # If engine URL has changed, recreate the session factory
    engine = get_engine()
    if _SessionLocal:
        try:
            # Ensure session factory is bound to the current engine
            # If not, recreate it
            if _SessionLocal.kw.get("bind") is engine:
                return _SessionLocal
        except Exception:
            pass
    _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    return _SessionLocal


def get_session():
    Session = get_session_factory()
    return Session()
