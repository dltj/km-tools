from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.orm import Session as SQLAlchemySession

from .config import Config, get_config

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


_engine: Engine | None = None
_engine_db_path: Path | None = None
_session_factory: sessionmaker[SQLAlchemySession] | None = None

_sqlite_conn: sqlite3.Connection | None = None
_sqlite_db_path: Path | None = None


def get_database_path(config: Config | None = None) -> Path:
    """
    Return the SQLite database path.

    If config.kmtools.dbfile is relative, resolve it relative to the
    directory containing the config file.
    """

    config = config or get_config()

    dbfile = config.kmtools.dbfile.expanduser()

    if dbfile.is_absolute():
        return dbfile

    return config.config_dir / dbfile


##
## This is the SQLAlchemy implementation
def get_engine(config: Config | None = None) -> Engine:
    """
    Return the SQLAlchemy engine for the configured database.

    The engine is created lazily so importing this module does not initialize
    configuration too early.
    """

    global _engine
    global _engine_db_path
    global _session_factory

    db_path = get_database_path(config)

    if _engine is None or _engine_db_path != db_path:
        if _engine is not None:
            _engine.dispose()

        db_path.parent.mkdir(parents=True, exist_ok=True)

        url = URL.create(
            "sqlite+pysqlite",
            database=str(db_path),
        )

        _engine = create_engine(
            url,
            connect_args={
                "timeout": 30,
            },
        )

        _engine_db_path = db_path
        _session_factory = None

    return _engine


def get_session_factory(
    config: Config | None = None,
) -> sessionmaker[SQLAlchemySession]:
    """
    Return a SQLAlchemy session factory bound to the configured engine.
    """

    global _session_factory

    engine = get_engine(config)

    if _session_factory is None:
        _session_factory = sessionmaker(bind=engine)

    return _session_factory


def get_session(config: Config | None = None) -> SQLAlchemySession:
    """
    Return a new SQLAlchemy Session.

    Usage:

        with get_session() as session:
            ...

    """

    return get_session_factory(config)()


##
## This is the older direct-to-sqlite3 implementation
def get_sqlite_connection(config: Config | None = None) -> sqlite3.Connection:
    """
    Return a cached sqlite3 connection for older code that uses sqlite3 directly.

    Prefer SQLAlchemy for new code.
    """

    global _sqlite_conn
    global _sqlite_db_path

    db_path = get_database_path(config)

    if _sqlite_conn is None or _sqlite_db_path != db_path:
        close_sqlite_connection()

        db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(
            db_path,
            timeout=30,
        )
        conn.row_factory = sqlite3.Row
        conn.set_trace_callback(logger.debug)

        _sqlite_conn = conn
        _sqlite_db_path = db_path

    return _sqlite_conn


def close_sqlite_connection() -> None:
    """
    Close the cached sqlite3 connection, if any.
    """

    global _sqlite_conn
    global _sqlite_db_path

    if _sqlite_conn is not None:
        _sqlite_conn.close()

    _sqlite_conn = None
    _sqlite_db_path = None


@contextmanager
def sqlite_transaction(
    config: Config | None = None,
    *,
    exclusive: bool = False,
) -> Iterator[sqlite3.Connection]:
    """
    Context manager for sqlite3 transaction use.

    Args:
        config:
            Optional Config object.

        exclusive:
            If True, start with BEGIN EXCLUSIVE.

    Usage:

        with sqlite_transaction(exclusive=True) as conn:
            conn.execute(...)
            conn.execute(...)

    """

    conn = get_sqlite_connection(config)

    if exclusive:
        conn.execute("BEGIN EXCLUSIVE")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def close_database() -> None:
    """
    Close cached database resources.

    Mostly useful for tests, or if you reinitialize configuration in the same
    process.
    """

    global _engine
    global _engine_db_path
    global _session_factory

    close_sqlite_connection()

    if _engine is not None:
        _engine.dispose()

    _engine = None
    _engine_db_path = None
    _session_factory = None
