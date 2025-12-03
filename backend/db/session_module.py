from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# NOTE: For initial scaffolding we read DATABASE_URL from env; later move to settings module.
import os

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
	raise ValueError(
		"DATABASE_URL environment variable is required. "
		"Example: postgresql+psycopg://user:pass@localhost:5432/dbname"
	)

engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)

Base = declarative_base()


def init_db() -> None:
	"""Create tables for the scaffolding phase (until Alembic migrations are added)."""
	from backend.modules.settings.organization.models import Organization  # noqa: F401
	from backend.modules.settings.models.settings_models import (  # noqa: F401
		Location,
		Permission,
		Role,
		RolePermission,
		User,
		UserRole,
	)

	Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
	db = SessionLocal()
	try:
		yield db
		db.commit()
	except Exception:
		db.rollback()
		raise
	finally:
		db.close()
