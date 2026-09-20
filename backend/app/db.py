"""Database setup and utilities."""
import os
from sqlmodel import SQLModel, create_engine, Session
from app.config import config


# Ensure data directory exists
os.makedirs(os.path.dirname(config.DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)

engine = create_engine(config.DATABASE_URL, echo=True)


def get_session():
    """Get database session."""
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    """Create database and all tables."""
    SQLModel.metadata.create_all(engine)
