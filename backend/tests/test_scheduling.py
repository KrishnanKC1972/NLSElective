from __future__ import annotations

from backend.app.scheduling import (
    SessionView,
    build_blocks,
    find_clashes,
    format_range,
    parse_day_block,
)
from backend.app.services import CourseSchedule


def test_parse_monday_two_periods():
    day, slots = parse_day_block(
        "Monday\n2.00 PM to 2.50 PM\n3:00 PM to 3:50 PM"
    )
    assert day == "Monday"
    assert [(slot.start_min, slot.end_min) for slot in slots] == [
        (840, 890),
        (900, 950),
    ]


def test_parse_afternoon_without_start_meridiem():
    day, slots = parse_day_block("Monday\n5:10 to 6:00 PM\n6.10 to 7.00 PM")
    assert day == "Monday"
    assert [(slot.start_min, slot.end_min) for slot in slots] == [
        (1030, 1080),
        (1090, 1140),
    ]


def test_parse_single_long_wednesday_block():
    day, slots = parse_day_block("Wednesday\n5.10 to 7.00 PM")
    assert day == "Wednesday"
    assert [(slot.start_min, slot.end_min) for slot in slots] == [(1030, 1140)]


def test_parse_saturday_morning_blocks():
    day, slots = parse_day_block(
        "Saturday\n9.00 AM to 9.50 AM\n10:00 AM to 10:50 AM"
    )
    assert day == "Saturday"
    assert [(slot.start_min, slot.end_min) for slot in slots] == [
        (540, 590),
        (600, 650),
    ]


def test_build_blocks_merges_periods_with_break():
    sessions = [
        SessionView("Monday", 0, 840, 890, ("R1",), ("A",)),
        SessionView("Monday", 0, 900, 950, ("R1",), ("A",)),
        SessionView("Wednesday", 2, 1030, 1140, ("R2",), ("B",)),
    ]
    blocks = build_blocks(sessions)
    assert len(blocks) == 2
    assert (blocks[0].start_min, blocks[0].end_min) == (840, 950)
    assert len(blocks[0].segments) == 2
    assert blocks[1].day == "Wednesday"


def test_format_range():
    assert format_range(840, 950) == "2:00\u20133:50 PM"
    assert format_range(670, 780) == "11:10 AM\u20131:00 PM"


def test_clash_detection_same_day_overlap():
    selected = CourseSchedule(
        course_id=1,
        title="Selected",
        sessions=[SessionView("Monday", 0, 840, 890)],
    )
    candidate = [SessionView("Monday", 0, 870, 900)]
    clashes = find_clashes(candidate, [selected])
    assert len(clashes) == 1
    assert clashes[0].overlap_start == 870
    assert clashes[0].overlap_end == 890


def test_no_clash_on_different_day_or_adjacent_time():
    selected = CourseSchedule(
        course_id=1,
        title="Selected",
        sessions=[SessionView("Monday", 0, 840, 890)],
    )
    assert not find_clashes([SessionView("Tuesday", 1, 840, 890)], [selected])
    assert not find_clashes([SessionView("Monday", 0, 890, 950)], [selected])
