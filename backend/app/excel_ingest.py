"""Import the elective catalogue and timetable into SQLite and map course names."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

import openpyxl
from sqlalchemy.orm import Session

from .config import (
    ELECTIVE_LIST_PATH,
    MAPPING_REPORT_PATH,
    TIMETABLE_PATH,
    TRIMESTER_LABEL,
)
from .database import Base, engine
from .models import ClassSession, Course
from .scheduling import DAY_INDEX, parse_day_block

LIST_HEADER_ROW = 1
TIMETABLE_HEADER_ROW = 3
MIN_TITLE_SIMILARITY = 0.74
MIN_TOTAL_SCORE = 0.80

MANUAL_ALIASES = {
    "law and economics": "twenty 20 law and economics",
    "twenty law and economics": "twenty 20 law and economics",
    "citizenship and immigration": (
        "citizenship and statelessness clinic ii drafting and research"
    ),
}


@dataclass
class TimetableCourseName:
    name: str
    normalized: str
    faculty: list[str]
    rows: int = 0


@dataclass
class ParsedTimetableRow:
    source_row: int
    timetable_name: str
    timetable_name_norm: str
    faculty: str
    classroom: str
    day: str
    start_min: int
    end_min: int
    day_block_raw: str


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = (
        text.replace("\u00a0", " ")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "-")
        .replace("\u2014", "-")
    )
    text = text.lower().replace("&", " and ")
    text = re.sub(r"['\"]", "", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(
        str(value)
        .replace("\u00a0", " ")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .split()
    )


def _truthy(value: Any) -> bool:
    return normalize_text(value) in {"yes", "y", "true", "1"}


def _as_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return 0.0


def title_similarity(first: str, second: str) -> float:
    if not first or not second:
        return 0.0
    if first == second:
        return 1.0
    ratio = SequenceMatcher(None, first, second).ratio()
    first_tokens, second_tokens = set(first.split()), set(second.split())
    if not first_tokens or not second_tokens:
        return ratio
    intersection = first_tokens & second_tokens
    containment = len(intersection) / min(len(first_tokens), len(second_tokens))
    jaccard = len(intersection) / len(first_tokens | second_tokens)
    token_score = 0.6 * containment + 0.4 * jaccard
    return max(ratio, token_score)


def _faculty_names(value: str) -> list[str]:
    text = (
        str(value or "")
        .replace("\u00a0", " ")
        .replace("\u2019", "'")
        .replace("\u2018", "'")
    )
    text = re.sub(r"\([^)]*\)", " ", text)
    parts = re.split(r"[;,/&]|\band\b", text, flags=re.IGNORECASE)
    names: list[str] = []
    for part in parts:
        normalized = normalize_text(part)
        normalized = re.sub(r"\b(prof|professor|dr|mr|ms|mrs)\b", " ", normalized)
        normalized = " ".join(normalized.split())
        if normalized:
            names.append(normalized)
    return names


def faculty_similarity(first: str, second: str) -> float:
    first_names = _faculty_names(first)
    second_names = _faculty_names(second)
    if not first_names or not second_names:
        return 0.0
    best = 0.0
    for left in first_names:
        for right in second_names:
            best = max(best, SequenceMatcher(None, left, right).ratio())
    return best


def parse_elective_list(path: Path) -> list[dict[str, Any]]:
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheet = workbook.worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [clean_text(cell) for cell in rows[LIST_HEADER_ROW - 1]]
    courses: list[dict[str, Any]] = []
    seen: set[str] = set()

    for row_number, row in enumerate(rows[LIST_HEADER_ROW:], start=LIST_HEADER_ROW + 1):
        if len(row) < 2:
            continue
        title = clean_text(row[1])
        if not title:
            continue
        title_norm = normalize_text(title)
        if title_norm in seen:
            continue
        seen.add(title_norm)

        faculty = clean_text(row[0])
        credits = _as_float(row[2]) if len(row) > 2 else 0.0
        concentration = clean_text(row[3]) if len(row) > 3 else ""
        eligibility: dict[str, bool] = {}
        audience: list[str] = []
        for index in range(7, len(headers)):
            header = headers[index]
            if not header or index >= len(row):
                continue
            is_eligible = _truthy(row[index])
            eligibility[header] = is_eligible
            if is_eligible:
                audience.append(header)

        courses.append(
            {
                "title": title,
                "title_norm": title_norm,
                "faculty": faculty,
                "credits": credits,
                "concentration": concentration or None,
                "survey_elective": _truthy(row[4]) if len(row) > 4 else False,
                "ba_practice": _truthy(row[5]) if len(row) > 5 else False,
                "clinical": _truthy(row[6]) if len(row) > 6 else False,
                "eligibility": eligibility,
                "audience": audience,
                "source_row": row_number,
            }
        )

    workbook.close()
    return courses


def parse_timetable(path: Path) -> tuple[list[ParsedTimetableRow], list[dict[str, Any]]]:
    workbook = openpyxl.load_workbook(path, data_only=True, read_only=True)
    sheet = workbook.worksheets[0]
    parsed: list[ParsedTimetableRow] = []
    problems: list[dict[str, Any]] = []
    current_block: str | None = None

    for row_number, row in enumerate(sheet.iter_rows(values_only=True), start=1):
        if row_number <= TIMETABLE_HEADER_ROW:
            continue
        if len(row) < 3:
            continue

        days_cell, faculty_cell, name_cell, room_cell = row[0], row[1], row[2], row[3]
        if days_cell is not None and str(days_cell).strip():
            current_block = str(days_cell)

        timetable_name = clean_text(name_cell)
        if not timetable_name:
            continue

        day, slots = parse_day_block(current_block)
        if not day or not slots:
            problems.append(
                {
                    "source_row": row_number,
                    "course_name": timetable_name,
                    "day_block": clean_text(current_block),
                    "reason": "Could not parse weekday or class times",
                }
            )
            continue

        for slot in slots:
            parsed.append(
                ParsedTimetableRow(
                    source_row=row_number,
                    timetable_name=timetable_name,
                    timetable_name_norm=normalize_text(timetable_name),
                    faculty=clean_text(faculty_cell),
                    classroom=clean_text(room_cell),
                    day=day,
                    start_min=slot.start_min,
                    end_min=slot.end_min,
                    day_block_raw=clean_text(current_block),
                )
            )

    workbook.close()
    return parsed, problems


def build_timetable_names(
    rows: Iterable[ParsedTimetableRow],
) -> list[TimetableCourseName]:
    grouped: dict[str, TimetableCourseName] = {}
    for row in rows:
        item = grouped.get(row.timetable_name_norm)
        if item is None:
            item = TimetableCourseName(
                name=row.timetable_name,
                normalized=row.timetable_name_norm,
                faculty=[],
            )
            grouped[row.timetable_name_norm] = item
        item.rows += 1
        if row.faculty and row.faculty not in item.faculty:
            item.faculty.append(row.faculty)
    return list(grouped.values())


def map_timetable_to_courses(
    timetable_names: list[TimetableCourseName],
    courses: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """Map every distinct timetable name onto a catalogue course.

    Matching is deliberately many-to-one: a course can be listed under more
    than one timetable name (for example a shortened title).
    """

    by_title: dict[str, dict[str, Any]] = {c["title_norm"]: c for c in courses}
    assignments: dict[str, dict[str, Any]] = {}
    report_rows: list[dict[str, Any]] = []

    for timetable_course in timetable_names:
        faculty = " ; ".join(timetable_course.faculty)
        alias_target = MANUAL_ALIASES.get(timetable_course.normalized)
        if alias_target and alias_target in by_title:
            target = by_title[alias_target]
            assignments[timetable_course.normalized] = {
                "course": target,
                "score": 1.0,
                "method": "manual_alias",
                "title_similarity": title_similarity(
                    timetable_course.normalized, alias_target
                ),
                "faculty_similarity": faculty_similarity(faculty, target["faculty"]),
            }
            report_rows.append(_mapping_report_row(timetable_course, target, assignments[timetable_course.normalized]))
            continue

        exact = by_title.get(timetable_course.normalized)
        if exact is not None:
            assignments[timetable_course.normalized] = {
                "course": exact,
                "score": 1.0,
                "method": "exact",
                "title_similarity": 1.0,
                "faculty_similarity": faculty_similarity(faculty, exact["faculty"]),
            }
            report_rows.append(_mapping_report_row(timetable_course, exact, assignments[timetable_course.normalized]))
            continue

        best: tuple[float, float, float, dict[str, Any]] | None = None
        for course in courses:
            title_score = title_similarity(
                timetable_course.normalized, course["title_norm"]
            )
            faculty_score = faculty_similarity(faculty, course["faculty"])
            total = 0.75 * title_score + 0.25 * faculty_score
            if best is None or total > best[0]:
                best = (total, title_score, faculty_score, course)

        if best is not None:
            total, title_score, faculty_score, target = best
            if title_score >= MIN_TITLE_SIMILARITY and total >= MIN_TOTAL_SCORE:
                assignments[timetable_course.normalized] = {
                    "course": target,
                    "score": total,
                    "method": "fuzzy",
                    "title_similarity": title_score,
                    "faculty_similarity": faculty_score,
                }
                report_rows.append(_mapping_report_row(timetable_course, target, assignments[timetable_course.normalized]))
            else:
                report_rows.append(
                    {
                        "timetable_name": timetable_course.name,
                        "timetable_name_norm": timetable_course.normalized,
                        "faculty": faculty,
                        "rows": timetable_course.rows,
                        "mapped": False,
                        "best_candidate": target["title"],
                        "score": round(total, 4),
                        "title_similarity": round(title_score, 4),
                        "faculty_similarity": round(faculty_score, 4),
                    }
                )
        else:
            report_rows.append(
                {
                    "timetable_name": timetable_course.name,
                    "timetable_name_norm": timetable_course.normalized,
                    "faculty": faculty,
                    "rows": timetable_course.rows,
                    "mapped": False,
                }
            )

    return assignments, report_rows


def _mapping_report_row(
    timetable_course: TimetableCourseName,
    target: dict[str, Any],
    assignment: dict[str, Any],
) -> dict[str, Any]:
    return {
        "timetable_name": timetable_course.name,
        "timetable_name_norm": timetable_course.normalized,
        "faculty": " ; ".join(timetable_course.faculty),
        "rows": timetable_course.rows,
        "mapped": True,
        "course_title": target["title"],
        "method": assignment["method"],
        "score": round(assignment["score"], 4),
        "title_similarity": round(assignment["title_similarity"], 4),
        "faculty_similarity": round(assignment["faculty_similarity"], 4),
    }


def ingest(
    list_path: Path = ELECTIVE_LIST_PATH,
    timetable_path: Path = TIMETABLE_PATH,
    report_path: Path = MAPPING_REPORT_PATH,
) -> dict[str, Any]:
    if not list_path.exists():
        raise FileNotFoundError(f"Elective list not found: {list_path}")
    if not timetable_path.exists():
        raise FileNotFoundError(f"Timetable not found: {timetable_path}")

    courses_data = parse_elective_list(list_path)
    timetable_rows, problems = parse_timetable(timetable_path)
    timetable_names = build_timetable_names(timetable_rows)
    assignments, mapping_report = map_timetable_to_courses(
        timetable_names, courses_data
    )

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        course_objects: dict[str, Course] = {}
        for payload in courses_data:
            course = Course(
                title=payload["title"],
                title_norm=payload["title_norm"],
                faculty=payload["faculty"],
                credits=payload["credits"],
                concentration=payload["concentration"],
                survey_elective=payload["survey_elective"],
                ba_practice=payload["ba_practice"],
                clinical=payload["clinical"],
                eligibility=payload["eligibility"],
                audience=payload["audience"],
                source_row=payload["source_row"],
            )
            db.add(course)
            course_objects[payload["title_norm"]] = course
        db.flush()

        method_counts: Counter[str] = Counter()
        mapped_sessions = 0
        unmapped_sessions = 0
        for row in timetable_rows:
            assignment = assignments.get(row.timetable_name_norm)
            course = assignment["course"] if assignment else None
            if course is None:
                unmapped_sessions += 1
            else:
                mapped_sessions += 1
                method_counts[assignment["method"]] += 1
            db.add(
                ClassSession(
                    course_id=course_objects[course["title_norm"]].id if course else None,
                    timetable_name=row.timetable_name,
                    timetable_name_norm=row.timetable_name_norm,
                    faculty=row.faculty,
                    classroom=row.classroom,
                    day=row.day,
                    day_index=DAY_INDEX[row.day],
                    start_min=row.start_min,
                    end_min=row.end_min,
                    day_block_raw=row.day_block_raw,
                    source_row=row.source_row,
                    match_score=assignment["score"] if assignment else 0.0,
                    match_method=assignment["method"] if assignment else "unmapped",
                )
            )
        db.commit()

        courses_without_schedule = [
            payload["title"]
            for payload in courses_data
            if payload["title_norm"] not in {
                assignment["course"]["title_norm"]
                for assignment in assignments.values()
            }
        ]

        summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "trimester": TRIMESTER_LABEL,
            "sources": {
                "elective_list": str(list_path),
                "timetable": str(timetable_path),
            },
            "counts": {
                "courses": len(courses_data),
                "timetable_rows": len(timetable_rows),
                "timetable_names": len(timetable_names),
                "mapped_timetable_names": sum(
                    1 for row in mapping_report if row["mapped"]
                ),
                "unmapped_timetable_names": sum(
                    1 for row in mapping_report if not row["mapped"]
                ),
                "mapped_sessions": mapped_sessions,
                "unmapped_sessions": unmapped_sessions,
                "courses_with_schedule": len(courses_data) - len(courses_without_schedule),
                "courses_without_schedule": len(courses_without_schedule),
                "match_methods": dict(method_counts),
            },
            "manual_aliases": MANUAL_ALIASES,
            "courses_without_schedule": courses_without_schedule,
            "unmapped_timetable_names": [
                row for row in mapping_report if not row["mapped"]
            ],
            "parse_problems": problems,
            "mapping": sorted(
                mapping_report, key=lambda row: row["timetable_name"].lower()
            ),
        }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return summary


def print_summary(summary: dict[str, Any]) -> None:
    counts = summary["counts"]
    print("Elective data imported")
    print(f"  Courses:                  {counts['courses']}")
    print(f"  Timetable rows:           {counts['timetable_rows']}")
    print(f"  Distinct timetable names: {counts['timetable_names']}")
    print(f"  Mapped names:             {counts['mapped_timetable_names']}")
    print(f"  Unmapped names:           {counts['unmapped_timetable_names']}")
    print(f"  Mapped sessions:          {counts['mapped_sessions']}")
    print(f"  Unmapped sessions:        {counts['unmapped_sessions']}")
    print(f"  Courses with no schedule: {counts['courses_without_schedule']}")
    if summary["courses_without_schedule"]:
        for title in summary["courses_without_schedule"]:
            print(f"    - {title}")
    if summary["unmapped_timetable_names"]:
        print("  Unmapped timetable names:")
        for row in summary["unmapped_timetable_names"]:
            print(
                f"    - {row['timetable_name']} "
                f"(best: {row.get('best_candidate', 'n/a')})"
            )
    if summary["parse_problems"]:
        print(f"  Parse problems: {len(summary['parse_problems'])}")
        for problem in summary["parse_problems"]:
            print(f"    - row {problem['source_row']}: {problem['course_name']}")
