from __future__ import annotations

import sqlite3
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base


def _make_engine() -> Engine:
    engine = create_engine(
        settings.DATABASE_URL,
        future=True,
        echo=False,
        pool_pre_ping=True,
    )

    # SQLite foreign keys (safe no-op on Postgres)
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON;")
            cursor.close()

    return engine


engine = _make_engine()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """
    MVP approach: create tables if they don't exist.
    (future case: replace with Alembic migrations.)
    """
    Base.metadata.create_all(bind=engine)