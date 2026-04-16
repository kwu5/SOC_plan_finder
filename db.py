from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal
from typing import Iterator

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Numeric,
    String,
    create_engine,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    relationship,
)

try:
    import streamlit as st
    _cache_resource = st.cache_resource
except Exception:
    def _cache_resource(fn):
        return fn


def _get_database_url() -> str:
    try:
        import streamlit as st
        if "DATABASE_URL" in st.secrets:
            return st.secrets["DATABASE_URL"]
    except Exception:
        pass
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL not configured. Set it in .streamlit/secrets.toml or as an env var."
        )
    return url


class Base(DeclarativeBase):
    pass


class Provider(Base):
    __tablename__ = "providers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    allow_multiple: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    plans: Mapped[list["Plan"]] = relationship(
        back_populates="provider", cascade="all, delete-orphan"
    )


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    premium: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    provider: Mapped[Provider] = relationship(back_populates="plans")

    __table_args__ = (CheckConstraint("premium >= 0", name="plans_premium_nonneg"),)


class ExclusionRule(Base):
    __tablename__ = "exclusion_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_a_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    plan_b_id: Mapped[int] = mapped_column(
        ForeignKey("plans.id", ondelete="CASCADE"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint("plan_a_id <> plan_b_id", name="exclusion_rules_distinct"),
    )


@_cache_resource
def get_engine():
    return create_engine(_get_database_url(), pool_pre_ping=True, future=True)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = Session(get_engine(), expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
