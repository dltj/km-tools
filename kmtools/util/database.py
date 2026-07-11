from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Define database URI and create engine.
DB_PATH = Path(__file__).resolve().parents[2] / "kmtools.sqlite3"
engine: Engine = create_engine(f"sqlite:///{DB_PATH}")

# Create a session factory bound to this engine
SessionFactory = sessionmaker(bind=engine)

Session = SessionFactory


class Base(DeclarativeBase):
    pass


# Use the global Session object to create and manage sessions
def get_session():
    return Session()
