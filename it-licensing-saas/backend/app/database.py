from __future__ import annotations
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLALCHEMY_DATABASE_URL = "sqlite:////workspace/it-licensing-saas/backend/app.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()