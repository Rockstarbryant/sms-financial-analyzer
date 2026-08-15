"""Shared pytest fixtures.

Each test gets a fresh, isolated SQLite file so tests never interfere with
each other or with any real data.
"""
from __future__ import annotations

import os
import tempfile
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Import here so app.database picks up a fresh engine bound to our temp file.
    from app.database import Base

    engine = create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})
    from app.models import transaction, user  # noqa: F401 - ensure models registered

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        os.remove(path)
