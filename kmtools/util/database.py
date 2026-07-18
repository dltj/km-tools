from __future__ import annotations

import logging
from pathlib import Path

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
