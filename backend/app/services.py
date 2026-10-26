"""Catalogue, planner and pricing-free business logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import MAX_ELECTIVES, TRIMESTER_LABEL
from .models import ClassSession, Course
from .scheduling import (
    BlockView,
    ClashDetail,
    CourseSchedule,
    SessionView,
    aggregate_sessions,
    build_blocks,
    find_clashes,
    format_duration,
    format_range,
    sessions_conflict,
    weekly_minutes,
)
from .schemas import (
    BlockOut,
    CandidateOut,
    ClashInfo,
    CourseOut,
    PlannerResponse,
    PlanSummary,
    SessionOut,
)

SHORT_DAY = {
    "Monday": "Mon",
    "Tuesday": "Tue",
    "Wednesday": "Wed",
    "Thursday": "Thu",
    "Friday": "Fri",
    "Saturday": "Sat",
    "Sunday": "Sun",
}


class SelectionError(ValueError):
    """Raised when a requested selection is invalid."""

    def __init__(self, message: str, clashes: list[ClashInfo] | None = None):
        super().__init__(message)
        self.clashes = clashes or []


@dataclass
class CatalogEntry:
    course: Course
    out: CourseOut
    sessions: list[SessionView]


def _session_out(session: SessionView) -> SessionOut:
    return SessionOut(
        day=session.day,
        day_index=session.day_index,
        start_min=session.start_min,
        end_min=session.end_min,
        start_label=session.start_label,
        end_label=session.end_label,
        time_label=session.time_label,
        duration_min=session.duration_min,
        duration_label=format_duration(session.duration_min),
        classrooms=list(session.classrooms),
        faculties=list(session.faculties),
    )


def _block_out(block: BlockView) -> BlockOut:
    return BlockOut(
        day=block.day,
        day_index=block.day_index,
        start_min=block.start_min,
        end_min=block.end_min,
        start_label=block.start_label,
        end_label=block.end_label,
        time_label=block.time_label,
        duration_min=block.duration_min,
        duration_label=block.duration_label,
        classrooms=block.classrooms,
        faculties=block.faculties,
        segments=[_session_out(segment) for segment in block.segments],
    )


def _schedule_label(blocks: Sequence[BlockView]) -> str:
    if not blocks:
        return "Timetable not published"
    return " \u00b7 ".join(
        f"{SHORT_DAY.get(block.day, block.day)} {block.time_label}" for block in blocks
    )


def _clash_info(detail: ClashDetail) -> ClashInfo:
    return ClashInfo(
        selected_course_id=detail.selected_course_id,
        selected_course_title=detail.selected_course_title,
        day=detail.day,
        day_index=detail.day_index,
        overlap_start=detail.overlap_start,
        overlap_end=detail.overlap_end,
        overlap_label=detail.overlap_label,
    )


def build_catalog(db: Session, program: str | None = None) -> list[CatalogEntry]:
    courses = list(db.scalars(select(Course).order_by(Course.title)).all())
    rows = list(
        db.scalars(
            select(ClassSession)
            .where(ClassSession.course_id.is_not(None))
            .order_by(ClassSession.day_index, ClassSession.start_min)
        ).all()
    )
    rows_by_course: dict[int, list[ClassSession]] = {}
    for row in rows:
        rows_by_course.setdefault(row.course_id, []).append(row)

    entries: list[CatalogEntry] = []
    for course in courses:
        if program and program.strip():
            eligibility = course.eligibility or {}
            program_key = None
            for k in eligibility.keys():
                if k.strip().lower() == program.strip().lower():
                    program_key = k
                    break
            if program_key is not None:
                if eligibility.get(program_key) is not True:
                    continue
            else:
                matched = False
                for k, v in eligibility.items():
                    if program.strip().lower() in k.strip().lower() or k.strip().lower() in program.strip().lower():
                        if v is True:
                            matched = True
                            break
                if not matched:
                    continue
        course_rows = rows_by_course.get(course.id, [])
        sessions = aggregate_sessions(
            (
                row.day,
                row.start_min,
                row.end_min,
                row.classroom,
                row.faculty,
            )
            for row in course_rows
        )
        blocks = build_blocks(sessions)
        timetable_names = sorted(
            {
                row.timetable_name
                for row in course_rows
                if row.timetable_name
            },
            key=str.lower,
        )
        out = CourseOut(
            id=course.id,
            title=course.title,
            faculty=course.faculty,
            credits=course.credits,
            concentration=course.concentration,
            survey_elective=course.survey_elective,
            ba_practice=course.ba_practice,
            clinical=course.clinical,
            eligibility=course.eligibility or {},
            audience=course.audience or [],
            timetable_names=timetable_names,
            sessions=[_session_out(session) for session in sessions],
            blocks=[_block_out(block) for block in blocks],
            schedule_label=_schedule_label(blocks),
            has_schedule=bool(sessions),
            session_count=len(sessions),
            day_count=len({session.day for session in sessions}),
            weekly_minutes=weekly_minutes(sessions),
        )
        entries.append(CatalogEntry(course=course, out=out, sessions=sessions))
    return entries


def _validate_selection(
    entries: dict[int, CatalogEntry], selected_ids: Sequence[int]
) -> list[CatalogEntry]:
    unique_ids: list[int] = []
    for course_id in selected_ids:
        if course_id not in unique_ids:
            unique_ids.append(course_id)
    if len(unique_ids) > MAX_ELECTIVES:
        raise SelectionError(
            f"You can select a maximum of {MAX_ELECTIVES} electives."
        )
    missing = [course_id for course_id in unique_ids if course_id not in entries]
    if missing:
        raise SelectionError(
            "Unknown elective id(s): " + ", ".join(str(value) for value in missing)
        )

    selected = [entries[course_id] for course_id in unique_ids]
    for index, first in enumerate(selected):
        for second in selected[index + 1 :]:
            if not sessions_conflict(first.sessions, second.sessions):
                continue
            details = find_clashes(
                second.sessions,
                [CourseSchedule(first.course.id, first.course.title, first.sessions)],
            )
            detail_text = (
                f"{details[0].day} {details[0].overlap_label}" if details else "overlapping time"
            )
            raise SelectionError(
                f"'{first.course.title}' clashes with '{second.course.title}' "
                f"({detail_text}). Remove one of them to continue.",
                [_clash_info(detail) for detail in details],
            )
    return selected


def build_planner(db: Session, selected_ids: Sequence[int]) -> PlannerResponse:
    return build_planner_from_catalog(build_catalog(db), selected_ids)


def build_planner_from_catalog(
    catalog: Sequence[CatalogEntry], selected_ids: Sequence[int]
) -> PlannerResponse:
    entries = {entry.course.id: entry for entry in catalog}
    selected_entries = _validate_selection(entries, selected_ids)
    selected_id_set = {entry.course.id for entry in selected_entries}
    selected_schedules = [
        CourseSchedule(entry.course.id, entry.course.title, entry.sessions)
        for entry in selected_entries
    ]

    candidates: list[CandidateOut] = []
    clash_ids: list[int] = []
    compatible_ids: list[int] = []
    unscheduled_ids: list[int] = []

    for entry in catalog:
        course = entry.out
        if entry.course.id in selected_id_set:
            status = "selected"
            clash_details: list[ClashDetail] = []
        elif not entry.sessions:
            status = "unscheduled"
            clash_details = []
            unscheduled_ids.append(entry.course.id)
        elif not selected_entries:
            status = "available"
            clash_details = []
        else:
            clash_details = find_clashes(entry.sessions, selected_schedules)
            if clash_details:
                status = "clash"
                clash_ids.append(entry.course.id)
            else:
                status = "compatible"
                compatible_ids.append(entry.course.id)

        candidates.append(
            CandidateOut(
                **course.model_dump(),
                status=status,
                clash_count=len({detail.selected_course_id for detail in clash_details}),
                clashes=[_clash_info(detail) for detail in clash_details],
            )
        )

    summary = PlanSummary(
        total_courses=len(catalog),
        selected_count=len(selected_entries),
        clash_count=len(clash_ids),
        compatible_count=len(compatible_ids),
        unscheduled_count=len(unscheduled_ids),
        remaining_slots=max(0, MAX_ELECTIVES - len(selected_entries)),
        total_credits=round(sum(entry.course.credits for entry in selected_entries), 2),
        max_electives=MAX_ELECTIVES,
    )

    return PlannerResponse(
        selected=[entry.out for entry in selected_entries],
        all=candidates,
        clash_ids=clash_ids,
        compatible_ids=compatible_ids,
        unscheduled_ids=unscheduled_ids,
        can_select_more=len(selected_entries) < MAX_ELECTIVES,
        max_electives=MAX_ELECTIVES,
        summary=summary,
        trimester=TRIMESTER_LABEL,
    )


def build_catalog_context(entries: Sequence[CatalogEntry], planner: PlannerResponse) -> str:
    status_by_id = {course.id: course.status for course in planner.all}
    clash_titles_by_id = {
        course.id: sorted(
            {clash.selected_course_title for clash in course.clashes}
        )
        for course in planner.all
    }

    lines = [
        f"TRIMESTER: {planner.trimester}",
        "CATALOGUE (all published course offerings):",
    ]
    for entry in entries:
        course = entry.out
        status = status_by_id.get(course.id, "unknown")
        status_text = status
        if status == "clash":
            clash_with = ", ".join(clash_titles_by_id.get(course.id, []))
            status_text = f"clash with {clash_with}" if clash_with else "clash"
        lines.append(
            f"[{course.id}] {course.title} | {course.faculty} | "
            f"{course.credits:g} credits | {course.schedule_label} | "
            f"{status_text}"
        )

    selected_titles = ", ".join(course.title for course in planner.selected) or "none"
    lines.extend(
        [
            "",
            f"SELECTED ({planner.summary.selected_count}/{planner.max_electives}): {selected_titles}",
            f"TOTAL SELECTED CREDITS: {planner.summary.total_credits:g}",
            f"COMPATIBLE COUNT: {planner.summary.compatible_count}",
            f"CLASH COUNT: {planner.summary.clash_count}",
            f"UNSCHEDULED COUNT: {planner.summary.unscheduled_count}",
            "",
            "PLANNER RULES:",
            f"- Students may choose at most {planner.max_electives} electives.",
            "- The first elective is unrestricted. Later choices must not overlap in day and time.",
            "- A clash means same weekday and overlapping clock time.",
            "- Use the schedule strings exactly as given. Do not invent rooms, times, credits or courses.",
        ]
    )
    return "\n".join(lines)


def planner_for_ids(
    db: Session, ids: Sequence[int]
) -> tuple[PlannerResponse, list[CatalogEntry]]:
    entries = build_catalog(db)
    response = build_planner_from_catalog(entries, ids)
    return response, entries


def _course_matches(entry: CatalogEntry, tokens: Iterable[str]) -> int:
    haystack = " ".join(
        [
            entry.out.title,
            entry.out.faculty,
            entry.out.concentration or "",
            entry.out.schedule_label,
        ]
    ).lower()
    return sum(1 for token in tokens if token and token in haystack)


def fallback_answer(
    question: str,
    entries: Sequence[CatalogEntry],
    planner: PlannerResponse,
) -> str:
    """Deterministic assistant used when Gemini is unavailable."""

    text = question.lower()
    selected = planner.selected
    selected_titles = ", ".join(course.title for course in selected)

    if not selected:
        tokens = [token for token in text.replace("?", " ").split() if len(token) > 3]
        matches = sorted(
            (
                (score, entry)
                for entry in entries
                if (score := _course_matches(entry, tokens)) > 0
            ),
            key=lambda item: (-item[0], item[1].out.title.lower()),
        )
        if matches:
            picks = "\n".join(
                f"- {entry.out.title} ({entry.out.credits:g} credits, {entry.out.faculty}) "
                f"\u2014 {entry.out.schedule_label}"
                for _, entry in matches[:6]
            )
            return (
                "Here are the closest catalogue matches:\n"
                f"{picks}\n\nPick any one as your first elective \u2014 the first choice "
                "is unrestricted. After that I can show compatible courses and clashes."
            )
        return (
            "You have not selected an elective yet. The first choice is unrestricted: "
            "pick any course from the catalogue. Once one is selected I can list the "
            f"clashing courses, the compatible courses, and the complete catalogue. "
            f"{planner.summary.total_courses} electives are loaded."
        )

    if any(word in text for word in ("clash", "conflict", "overlap")):
        clashes = [course for course in planner.all if course.status == "clash"]
        if not clashes:
            return (
                "No other catalogue course clashes with your current selection. "
                f"All {planner.summary.compatible_count} scheduled courses are compatible."
            )
        shown = "\n".join(
            f"- {course.title} \u2014 clashes with "
            + ", ".join(sorted({item.selected_course_title for item in course.clashes}))
            + f" ({course.clash_count} selected course{'s' if course.clash_count != 1 else ''})"
            for course in clashes[:12]
        )
        remainder = len(clashes) - 12
        suffix = f"\n- ...and {remainder} more" if remainder > 0 else ""
        return (
            f"{len(clashes)} courses clash with your selected elective "
            f"({selected_titles}):\n{shown}{suffix}\n\n"
            "Those courses share a weekday and overlapping class time."
        )

    if any(word in text for word in ("compatible", "free", "suggest", "recommend", "another", "next")):
        compatible = [
            course for course in planner.all if course.status == "compatible"
        ]
        if not compatible:
            return (
                "There are no clash-free scheduled courses left for the current selection. "
                "Remove one of your selected electives to free up a slot."
            )
        shown = "\n".join(
            f"- {course.title} ({course.credits:g} credits) \u2014 {course.schedule_label}"
            for course in compatible[:10]
        )
        return (
            f"{len(compatible)} courses are compatible with {selected_titles}:\n"
            f"{shown}\n\n"
            f"You have {planner.summary.remaining_slots} slot(s) remaining."
        )

    if any(word in text for word in ("calendar", "schedule", "timetable", "week")):
        lines = []
        for course in selected:
            lines.append(f"- {course.title}: {course.schedule_label}")
        return (
            "Your weekly schedule:\n"
            + "\n".join(lines)
            + f"\n\nTotal credits: {planner.summary.total_credits:g}."
        )

    if any(word in text for word in ("credit", "how many", "count", "summary", "selected", "my")):
        return (
            f"You have selected {planner.summary.selected_count} of "
            f"{planner.max_electives} electives ({planner.summary.total_credits:g} credits): "
            f"{selected_titles}. "
            f"{planner.summary.compatible_count} scheduled courses are compatible and "
            f"{planner.summary.clash_count} clash with the current selection."
        )

    tokens = [token for token in text.replace("?", " ").split() if len(token) > 3]
    matches = sorted(
        (
            (score, entry)
            for entry in entries
            if (score := _course_matches(entry, tokens)) > 0
        ),
        key=lambda item: (-item[0], item[1].out.title.lower()),
    )
    if matches:
        picks = "\n".join(
            f"- {entry.out.title} ({entry.out.credits:g} credits) \u2014 {entry.out.schedule_label}"
            for _, entry in matches[:5]
        )
        return (
            f"Your selection: {selected_titles}.\nClosest catalogue matches:\n{picks}\n\n"
            "Ask me about clashes, compatible options, or your weekly calendar."
        )

    return (
        f"Your selection: {selected_titles}. "
        f"{planner.summary.compatible_count} scheduled courses are compatible, "
        f"{planner.summary.clash_count} clash, and {planner.summary.unscheduled_count} "
        "have no published timetable. Ask about clashes, compatible courses, or the calendar."
    )
