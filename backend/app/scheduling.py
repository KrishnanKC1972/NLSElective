"""Timetable parsing, display helpers and clash detection."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Sequence

DAY_ORDER = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
DAY_INDEX = {day: index for index, day in enumerate(DAY_ORDER)}
DAY_LOOKUP = {day.lower(): day for day in DAY_ORDER}

_TIME_RANGE = re.compile(
    r"(?P<sh>\d{1,2})[.:](?P<sm>\d{2})\s*(?P<smer>am|pm)?"
    r"\s*(?:to|till|until|-|\u2013|\u2014)\s*"
    r"(?P<eh>\d{1,2})[.:](?P<em>\d{2})\s*(?P<emer>am|pm)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParsedSlot:
    start_min: int
    end_min: int
    text: str


@dataclass(frozen=True)
class SessionView:
    day: str
    day_index: int
    start_min: int
    end_min: int
    classrooms: tuple[str, ...] = ()
    faculties: tuple[str, ...] = ()

    @property
    def start_label(self) -> str:
        return format_time(self.start_min)

    @property
    def end_label(self) -> str:
        return format_time(self.end_min)

    @property
    def time_label(self) -> str:
        return format_range(self.start_min, self.end_min)

    @property
    def duration_min(self) -> int:
        return self.end_min - self.start_min


@dataclass
class BlockView:
    day: str
    day_index: int
    start_min: int
    end_min: int
    segments: list[SessionView] = field(default_factory=list)

    @property
    def start_label(self) -> str:
        return format_time(self.start_min)

    @property
    def end_label(self) -> str:
        return format_time(self.end_min)

    @property
    def time_label(self) -> str:
        return format_range(self.start_min, self.end_min)

    @property
    def duration_min(self) -> int:
        return self.end_min - self.start_min

    @property
    def duration_label(self) -> str:
        return format_duration(self.duration_min)

    @property
    def classrooms(self) -> list[str]:
        return _unique(item for segment in self.segments for item in segment.classrooms)

    @property
    def faculties(self) -> list[str]:
        return _unique(item for segment in self.segments for item in segment.faculties)


@dataclass(frozen=True)
class ClashDetail:
    selected_course_id: int
    selected_course_title: str
    day: str
    overlap_start: int
    overlap_end: int

    @property
    def day_index(self) -> int:
        return DAY_INDEX[self.day]

    @property
    def overlap_label(self) -> str:
        return format_range(self.overlap_start, self.overlap_end)


@dataclass
class CourseSchedule:
    """A course paired with its mapped sessions."""

    course_id: int
    title: str
    sessions: list[SessionView]


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        cleaned = (value or "").strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _to_minutes(hour: str | int, minute: str | int, meridiem: str | None) -> int:
    h = int(hour)
    m = int(minute)
    if meridiem:
        meridiem = meridiem.lower()
        if meridiem == "pm" and h != 12:
            h += 12
        elif meridiem == "am" and h == 12:
            h = 0
    return h * 60 + m


def _infer_meridiem(
    start_hour: int,
    end_hour: int,
    start_mer: str | None,
    end_mer: str | None,
) -> tuple[str | None, str | None]:
    if start_mer and end_mer:
        return start_mer.lower(), end_mer.lower()

    if end_mer and not start_mer:
        end_mer = end_mer.lower()
        # "11.10 to 12.00 PM" means 11:10 AM, not 11:10 PM.
        if end_mer == "pm" and end_hour == 12 and start_hour < 12:
            start_mer = "am"
        else:
            start_mer = end_mer
        return start_mer, end_mer

    if start_mer and not end_mer:
        start_mer = start_mer.lower()
        end_mer = start_mer
        if start_mer == "am" and end_hour == 12:
            end_mer = "pm"
        return start_mer, end_mer

    # No meridiem at all: use a conservative campus-hours heuristic.
    start_mer = "am" if 7 <= start_hour <= 11 else "pm"
    end_mer = "am" if 7 <= end_hour <= 11 else "pm"
    if start_mer == "am" and end_hour == 12:
        end_mer = "pm"
    return start_mer, end_mer


def parse_time_ranges(text: str) -> list[ParsedSlot]:
    """Parse every ``HH.MM [AM] to HH.MM [AM/PM]`` range in ``text``."""

    slots: list[ParsedSlot] = []
    for match in _TIME_RANGE.finditer(text or ""):
        groups = match.groupdict()
        start_mer, end_mer = _infer_meridiem(
            int(groups["sh"]),
            int(groups["eh"]),
            groups["smer"],
            groups["emer"],
        )
        start = _to_minutes(groups["sh"], groups["sm"], start_mer)
        end = _to_minutes(groups["eh"], groups["em"], end_mer)
        if end <= start:
            continue
        if not (0 <= start < 24 * 60 and 0 < end <= 24 * 60):
            continue
        slots.append(ParsedSlot(start, end, " ".join(match.group(0).split())))
    return slots


def parse_day_block(raw: str | None) -> tuple[str | None, list[ParsedSlot]]:
    """Parse a merged "Days" cell into a day plus its class ranges.

    The source file puts the weekday and all class times in one merged cell,
    for example ``Monday\\n2.00 PM to 2.50 PM\\n3:00 PM to 3:50 PM``.
    """

    if not raw or not str(raw).strip():
        return None, []

    lines = [line.strip() for line in str(raw).splitlines() if line.strip()]
    day: str | None = None
    if lines:
        first_word = re.split(r"[\s/,]+", lines[0], maxsplit=1)[0].strip()
        day = DAY_LOOKUP.get(first_word.lower())

    text = " ".join(lines)
    return day, parse_time_ranges(text)


def format_time(minutes: int) -> str:
    minutes = int(minutes)
    hour, minute = divmod(minutes, 60)
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {suffix}"


def format_range(start_min: int, end_min: int) -> str:
    start_suffix = "AM" if start_min < 720 else "PM"
    end_suffix = "AM" if end_min < 720 else "PM"
    if start_suffix == end_suffix:
        start_hour, start_minute = divmod(start_min, 60)
        end_hour, end_minute = divmod(end_min, 60)
        return (
            f"{start_hour % 12 or 12}:{start_minute:02d}"
            f"\u2013{end_hour % 12 or 12}:{end_minute:02d} {end_suffix}"
        )
    return f"{format_time(start_min)}\u2013{format_time(end_min)}"


def format_duration(minutes: int) -> str:
    hours, mins = divmod(int(minutes), 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if mins:
        parts.append(f"{mins}m")
    return " ".join(parts) or "0m"


def aggregate_sessions(
    rows: Iterable[tuple[str, int, int, str, str]],
) -> list[SessionView]:
    """Deduplicate sessions and collect rooms/faculty per day+time."""

    grouped: dict[tuple[int, int, int], dict[str, list[str]]] = {}
    for day, start_min, end_min, classroom, faculty in rows:
        if day not in DAY_INDEX:
            continue
        key = (DAY_INDEX[day], int(start_min), int(end_min))
        bucket = grouped.setdefault(key, {"rooms": [], "faculty": []})
        if classroom:
            bucket["rooms"].append(classroom)
        if faculty:
            bucket["faculty"].append(faculty)

    sessions: list[SessionView] = []
    for (day_index, start_min, end_min), bucket in sorted(grouped.items()):
        sessions.append(
            SessionView(
                day=DAY_ORDER[day_index],
                day_index=day_index,
                start_min=start_min,
                end_min=end_min,
                classrooms=tuple(_unique(bucket["rooms"])),
                faculties=tuple(_unique(bucket["faculty"])),
            )
        )
    return sessions


def build_blocks(sessions: Sequence[SessionView], gap_minutes: int = 15) -> list[BlockView]:
    """Merge back-to-back class periods (e.g. 2:00-2:50 then 3:00-3:50)."""

    blocks: list[BlockView] = []
    by_day: dict[int, list[SessionView]] = {}
    for session in sessions:
        by_day.setdefault(session.day_index, []).append(session)

    for day_index in sorted(by_day):
        day_sessions = sorted(by_day[day_index], key=lambda item: (item.start_min, item.end_min))
        current: BlockView | None = None
        for session in day_sessions:
            if (
                current is not None
                and session.start_min - current.end_min <= gap_minutes
            ):
                current.end_min = max(current.end_min, session.end_min)
                current.segments.append(session)
            else:
                current = BlockView(
                    day=session.day,
                    day_index=session.day_index,
                    start_min=session.start_min,
                    end_min=session.end_min,
                    segments=[session],
                )
                blocks.append(current)

    return sorted(blocks, key=lambda item: (item.day_index, item.start_min))


def overlaps(first: SessionView, second: SessionView) -> bool:
    return (
        first.day_index == second.day_index
        and first.start_min < second.end_min
        and second.start_min < first.end_min
    )


def find_clashes(
    candidate_sessions: Sequence[SessionView],
    selected: Sequence[CourseSchedule],
) -> list[ClashDetail]:
    """Return distinct overlaps between a candidate and selected courses."""

    details: dict[tuple[int, int, int, int], ClashDetail] = {}
    for course in selected:
        for candidate_session in candidate_sessions:
            for selected_session in course.sessions:
                if not overlaps(candidate_session, selected_session):
                    continue
                overlap_start = max(candidate_session.start_min, selected_session.start_min)
                overlap_end = min(candidate_session.end_min, selected_session.end_min)
                key = (
                    course.course_id,
                    candidate_session.day_index,
                    overlap_start,
                    overlap_end,
                )
                details.setdefault(
                    key,
                    ClashDetail(
                        selected_course_id=course.course_id,
                        selected_course_title=course.title,
                        day=candidate_session.day,
                        overlap_start=overlap_start,
                        overlap_end=overlap_end,
                    ),
                )
    return sorted(
        details.values(),
        key=lambda item: (item.day_index, item.overlap_start, item.selected_course_id),
    )


def sessions_conflict(
    first: Sequence[SessionView], second: Sequence[SessionView]
) -> bool:
    return any(overlaps(a, b) for a in first for b in second)


def weekly_minutes(sessions: Sequence[SessionView]) -> int:
    return sum(session.duration_min for session in sessions)
