from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Define database URI and create engine
engine: Engine = create_engine("sqlite:///kmtools.sqlite3")

# Create a session factory bound to this engine
SessionFactory = sessionmaker(bind=engine)

Session = SessionFactory


class Base(DeclarativeBase):
    pass


# Use the global Session object to create and manage sessions
def get_session():
    return Session()
