"""SQLAlchemy engine + session factory for review_ui (read-only).

Builds the engine from ``config.database_url``. Normalizes Railway/Heroku-style
``postgres://`` / ``postgresql://`` URLs to the ``postgresql+psycopg://`` driver
(psycopg3, the one shipped in requirements) — the same fix the live apps'
entrypoints apply, repeated here so local ``python`` runs work without the
entrypoint shell script.

This app NEVER creates or migrates schema. ``get_session`` rolls back on exit
rather than committing, since no write should ever happen here.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from review_ui.config import load_config


def _normalize_pg_url(url: str) -> str:
    """Make the Postgres driver explicit so SQLAlchemy doesn't reach for psycopg2."""
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url  # already explicit, or sqlite — leave as-is


def _build_engine() -> Engine:
    config = load_config()
    url = _normalize_pg_url(config.database_url)
    connect_args: dict = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    # pool_pre_ping guards against stale connections to a long-lived remote DB.
    return create_engine(
        url, connect_args=connect_args, pool_pre_ping=True, future=True
    )


engine: Engine = _build_engine()

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a read-only Session; always rolls back (this app never writes)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
