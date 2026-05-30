import getpass
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Пользователь PostgreSQL — НЕ логин админки сайта (admin/admin123).
# На Mac после Homebrew обычно совпадает с именем учётной записи macOS.
_pg_user = os.getenv("PGUSER", getpass.getuser())
_default_uri = f"postgresql://{_pg_user}@localhost:5432/fitness_db"

DATABASE_URI = os.getenv("DATABASE_URL", _default_uri)
# Render, Railway и др. отдают postgres:// — SQLAlchemy ждёт postgresql://
if DATABASE_URI.startswith("postgres://"):
    DATABASE_URI = "postgresql://" + DATABASE_URI[len("postgres://") :]

_engine_kwargs = {"echo": False}
if DATABASE_URI.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URI, **_engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
