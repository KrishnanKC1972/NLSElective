"""CLI entry point: python -m backend.scripts.ingest"""

from __future__ import annotations

import argparse
from pathlib import Path

from backend.app.config import ELECTIVE_LIST_PATH, MAPPING_REPORT_PATH, TIMETABLE_PATH
from backend.app.excel_ingest import ingest, print_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Map elective titles to timetable course names and rebuild the SQLite database."
    )
    parser.add_argument(
        "--list",
        dest="list_path",
        type=Path,
        default=ELECTIVE_LIST_PATH,
        help="Path to the elective list workbook.",
    )
    parser.add_argument(
        "--timetable",
        dest="timetable_path",
        type=Path,
        default=TIMETABLE_PATH,
        help="Path to the timetable workbook.",
    )
    parser.add_argument(
        "--report",
        dest="report_path",
        type=Path,
        default=MAPPING_REPORT_PATH,
        help="Where to write the JSON mapping audit report.",
    )
    args = parser.parse_args()
    summary = ingest(args.list_path, args.timetable_path, args.report_path)
    print_summary(summary)
    print(f"\nMapping report: {args.report_path}")


if __name__ == "__main__":
    main()
