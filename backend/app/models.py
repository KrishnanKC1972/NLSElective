"""Database models for the elective catalogue and mapped timetable sessions."""

from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from .database import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_norm: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    faculty: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    credits: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    concentration: Mapped[str | None] = mapped_column(String(120))
    survey_elective: Mapped[bool] = mapped_column(default=False)
    ba_practice: Mapped[bool] = mapped_column(default=False)
    clinical: Mapped[bool] = mapped_column(default=False)
    eligibility: Mapped[dict] = mapped_column(JSON, default=dict)
    audience: Mapped[list] = mapped_column(JSON, default=list)
    source_row: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    sessions: Mapped[list[ClassSession]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
    )


class ClassSession(Base):
    __tablename__ = "class_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=True, index=True
    )
    timetable_name: Mapped[str] = mapped_column(String(500), nullable=False)
    timetable_name_norm: Mapped[str] = mapped_column(
        String(500), nullable=False, index=True
    )
    faculty: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    classroom: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    day: Mapped[str] = mapped_column(String(12), nullable=False)
    day_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    start_min: Mapped[int] = mapped_column(Integer, nullable=False)
    end_min: Mapped[int] = mapped_column(Integer, nullable=False)
    day_block_raw: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source_row: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    match_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    match_method: Mapped[str] = mapped_column(String(40), nullable=False, default="")

    course: Mapped[Course | None] = relationship(back_populates="sessions")

    __table_args__ = (
        Index("ix_sessions_day_start", "day_index", "start_min", "end_min"),
    )
