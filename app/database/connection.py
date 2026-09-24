"""
Database engine & session management.

Responsible for creating the SQLite engine, creating all tables on first
run, and providing a session-per-operation context manager used by the
repository layer.
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config.settings import DATABASE_URL, DATABASE_FILE

logger = logging.getLogger("wdf.database")

_engine: Engine | None = None
_SessionFactory: sessionmaker | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            echo=False,
            future=True,
            connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
        )

        if DATABASE_URL.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def _set_sqlite_pragma(dbapi_connection, _record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    return _SessionFactory


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope for a series of operations."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Database transaction failed, rolled back.")
        raise
    finally:
        session.close()


def is_database_initialized() -> bool:
    return DATABASE_FILE.exists() and DATABASE_FILE.stat().st_size > 0


def init_database() -> bool:
    """
    Create all tables if they do not exist yet.

    Returns True if this is a first-time initialization (so the caller can
    decide to seed demo data), False if the database already existed.
    """
    from app.database.base import Base
    # Importing models package registers all model classes on Base.metadata.
    import app.database.models  # noqa: F401

    first_run = not is_database_initialized()
    Base.metadata.create_all(get_engine())
    if first_run:
        logger.info("Database created at %s", DATABASE_FILE)
    return first_run
