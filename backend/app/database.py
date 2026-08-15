from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from app.config import settings


if settings.is_postgres:
    database_url = settings.database_url

    # SQLAlchemy + psycopg 3
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace(
            "postgresql://",
            "postgresql+psycopg://",
            1,
        )

    elif database_url.startswith("postgres://"):
        database_url = database_url.replace(
            "postgres://",
            "postgresql+psycopg://",
            1,
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
    )

else:
    engine = create_engine(
        settings.database_url,
        connect_args={
            "check_same_thread": False,
        },
    )


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import transaction, user  # noqa: F401

    Base.metadata.create_all(bind=engine)