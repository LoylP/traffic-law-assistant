# -*- coding: utf-8 -*-
"""SQLAlchemy models for document store."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Document(Base):
    """Maps OpenSearch document id to violation_id."""

    __tablename__ = "document"

    opensearch_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    violation_id: Mapped[str] = mapped_column(String(255), nullable=False)
