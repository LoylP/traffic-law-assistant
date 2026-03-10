# -*- coding: utf-8 -*-
"""Document store using SQLAlchemy (OpenSearch doc id <-> violation_id)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import get_settings
from src.search.models import Base, Document


def get_db_path() -> Path:
    s = get_settings()
    p = Path(s.sqlite_document_db)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent.parent.parent / p
    return p


def get_engine():
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine("sqlite:///" + str(path), echo=False)


def get_session_factory():
    engine = get_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


_session_factory: sessionmaker | None = None


def get_session() -> Session:
    global _session_factory
    if _session_factory is None:
        _session_factory = get_session_factory()
    return _session_factory()


def ensure_document_table() -> None:
    """Create document table if it does not exist."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def save_document_id(opensearch_id: str, violation_id: str) -> None:
    with get_session() as session:
        doc = session.get(Document, opensearch_id)
        if doc:
            doc.violation_id = violation_id
        else:
            session.add(Document(opensearch_id=opensearch_id, violation_id=violation_id))
        session.commit()
