"""Factoría de engine/sesión SQLAlchemy. Funciona con sqlite:// y postgresql:// (Supabase)."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.database.models import Base

_engine = None
_SessionLocal: sessionmaker | None = None


def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    url = settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        # Crea el directorio de la BD si hace falta (p. ej. data/bot.db)
        db_path = url.replace("sqlite:///", "", 1)
        if db_path and db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}

    _engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    return _engine


def init_db() -> None:
    """Crea las tablas si no existen. Idempotente."""
    Base.metadata.create_all(get_engine())


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


@contextmanager
def session_scope():
    """Context manager: `with session_scope() as session: ...` con commit/rollback automático."""
    session: Session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
