from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    objective: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Extra fields needed for production usefulness (space + reproducibility knobs)
    space_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False, default=42)
    random_exploration_trials: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    trials: Mapped[list["Trial"]] = relationship("Trial", back_populates="experiment", cascade="all, delete-orphan")


class Trial(Base):
    __tablename__ = "trials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment_id: Mapped[int] = mapped_column(Integer, ForeignKey("experiments.id"), nullable=False, index=True)

    params_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    reward: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # suggested|completed|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    experiment: Mapped[Experiment] = relationship("Experiment", back_populates="trials")