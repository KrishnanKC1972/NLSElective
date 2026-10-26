"""Pydantic response models for the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SessionOut(BaseModel):
    day: str
    day_index: int
    start_min: int
    end_min: int
    start_label: str
    end_label: str
    time_label: str
    duration_min: int
    duration_label: str
    classrooms: list[str]
    faculties: list[str]


class BlockOut(BaseModel):
    day: str
    day_index: int
    start_min: int
    end_min: int
    start_label: str
    end_label: str
    time_label: str
    duration_min: int
    duration_label: str
    classrooms: list[str]
    faculties: list[str]
    segments: list[SessionOut]


class CourseOut(BaseModel):
    id: int
    title: str
    faculty: str
    credits: float
    concentration: str | None = None
    survey_elective: bool
    ba_practice: bool
    clinical: bool
    eligibility: dict[str, bool]
    audience: list[str]
    timetable_names: list[str]
    sessions: list[SessionOut]
    blocks: list[BlockOut]
    schedule_label: str
    has_schedule: bool
    session_count: int
    day_count: int
    weekly_minutes: int


class ClashInfo(BaseModel):
    selected_course_id: int
    selected_course_title: str
    day: str
    day_index: int
    overlap_start: int
    overlap_end: int
    overlap_label: str


CourseStatus = Literal["selected", "available", "compatible", "clash", "unscheduled"]


class CandidateOut(CourseOut):
    status: CourseStatus
    clash_count: int = 0
    clashes: list[ClashInfo] = Field(default_factory=list)


class PlanSummary(BaseModel):
    total_courses: int
    selected_count: int
    clash_count: int
    compatible_count: int
    unscheduled_count: int
    remaining_slots: int
    total_credits: float
    max_electives: int


class PlannerResponse(BaseModel):
    selected: list[CourseOut]
    all: list[CandidateOut]
    clash_ids: list[int]
    compatible_ids: list[int]
    unscheduled_ids: list[int]
    can_select_more: bool
    max_electives: int
    summary: PlanSummary
    trimester: str


class PlannerRequest(BaseModel):
    selected_ids: list[int] = Field(default_factory=list, max_length=4)
    program: str | None = None


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    selected_ids: list[int] = Field(default_factory=list, max_length=4)
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)


class ChatResponse(BaseModel):
    answer: str
    provider: Literal["gemini", "fallback"]
    model: str | None = None


class HealthResponse(BaseModel):
    status: str
    database: str
    courses: int
    sessions: int
    mapped_sessions: int
    unmapped_sessions: int
    llm_configured: bool
    llm_model: str
    trimester: str
    max_electives: int
