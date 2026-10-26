"""FastAPI application exposing the elective planner and LLM assistant."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import (
    ALLOWED_ORIGINS,
    DB_PATH,
    FRONTEND_DIST,
    MAPPING_REPORT_PATH,
    MAX_ELECTIVES,
    TRIMESTER_LABEL,
)
from .database import Base, SessionLocal, engine, get_db
from .excel_ingest import ingest, print_summary
from .llm_assistant import assistant
from .models import ClassSession, Course
from .schemas import (
    ChatRequest,
    ChatResponse,
    CourseOut,
    HealthResponse,
    PlannerRequest,
    PlannerResponse,
)
from .services import (
    SelectionError,
    build_catalog,
    build_catalog_context,
    build_planner_from_catalog,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        course_count = db.scalar(select(func.count()).select_from(Course)) or 0
    if course_count == 0:
        try:
            print_summary(ingest())
        except Exception:  # pragma: no cover - depends on source files
            logger.exception(
                "Database is empty and automatic import failed. "
                "Run: python -m backend.scripts.ingest"
            )
    yield


app = FastAPI(
    title="NLS Elective Planner",
    description=(
        "Elective catalogue, timetable clash detection, weekly calendar data "
        "and a Gemini-powered planning assistant."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _selection_error(exc: SelectionError) -> HTTPException:
    return HTTPException(
        status_code=400,
        detail={
            "message": str(exc),
            "clashes": [clash.model_dump() for clash in exc.clashes],
        },
    )


@app.get("/api/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    courses = db.scalar(select(func.count()).select_from(Course)) or 0
    sessions = db.scalar(select(func.count()).select_from(ClassSession)) or 0
    mapped = (
        db.scalar(
            select(func.count())
            .select_from(ClassSession)
            .where(ClassSession.course_id.is_not(None))
        )
        or 0
    )
    return HealthResponse(
        status="ok",
        database=str(DB_PATH),
        courses=courses,
        sessions=sessions,
        mapped_sessions=mapped,
        unmapped_sessions=sessions - mapped,
        llm_configured=assistant.configured,
        llm_model=assistant.model,
        trimester=TRIMESTER_LABEL,
        max_electives=MAX_ELECTIVES,
    )


@app.get("/api/courses", response_model=list[CourseOut])
def courses(program: str | None = None, db: Session = Depends(get_db)) -> list[CourseOut]:
    entries = build_catalog(db)
    if program and program.strip():
        filtered = []
        for entry in entries:
            eligibility = entry.out.eligibility or {}
            # Check if program is eligible - case insensitive match
            program_key = None
            for k in eligibility.keys():
                if k.strip().lower() == program.strip().lower():
                    program_key = k
                    break
            if program_key is not None and eligibility.get(program_key) is True:
                filtered.append(entry)
            elif program_key is None:
                # If program not found as exact key, try to match partially
                # Also check common variations
                for k, v in eligibility.items():
                    if program.strip().lower() in k.strip().lower() or k.strip().lower() in program.strip().lower():
                        if v is True:
                            filtered.append(entry)
                            break
                else:
                    continue  # not found/eligible
            else:
                continue  # explicitly NO
        return [entry.out for entry in filtered]
    return [entry.out for entry in entries]


@app.post("/api/plans/recommendations", response_model=PlannerResponse)
def recommendations(
    payload: PlannerRequest, db: Session = Depends(get_db)
) -> PlannerResponse:
    try:
        entries = build_catalog(db, program=payload.program)
        return build_planner_from_catalog(entries, payload.selected_ids)
    except SelectionError as exc:
        raise _selection_error(exc) from exc


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    entries = build_catalog(db)
    try:
        planner = build_planner_from_catalog(entries, payload.selected_ids)
    except SelectionError as exc:
        raise _selection_error(exc) from exc

    context = build_catalog_context(entries, planner)
    return await assistant.answer(
        question=payload.message,
        context=context,
        history=payload.history,
        entries=entries,
        planner=planner,
    )


@app.get("/api/mapping")
def mapping() -> dict:
    if not MAPPING_REPORT_PATH.exists():
        raise HTTPException(
            status_code=404,
            detail="Mapping report not found. Run the import script first.",
        )
    return json.loads(MAPPING_REPORT_PATH.read_text(encoding="utf-8"))


if FRONTEND_DIST.exists():
    assets_dir = FRONTEND_DIST / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")

    if FRONTEND_DIST.exists():
        candidate = (FRONTEND_DIST / full_path).resolve()
        try:
            candidate.relative_to(FRONTEND_DIST.resolve())
        except ValueError:
            raise HTTPException(status_code=404, detail="Not found")
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)

    if not full_path:
        return {
            "message": "NLS Elective Planner API is running.",
            "docs": "/docs",
            "frontend": "Build the React app in frontend/ to serve the UI here.",
        }
    raise HTTPException(status_code=404, detail="Not found")
