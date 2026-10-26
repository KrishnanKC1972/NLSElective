"""Application configuration loaded from the project .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = Path(os.getenv("SQLITE_PATH", str(DATA_DIR / "electives.db"))).resolve()
if not DB_PATH.is_absolute():
    DB_PATH = (BASE_DIR / DB_PATH).resolve()

ELECTIVE_LIST_PATH = Path(
    os.getenv("ELECTIVE_LIST_PATH", str(BASE_DIR / "Elective List.xlsx"))
).resolve()
TIMETABLE_PATH = Path(
    os.getenv(
        "TIMETABLE_PATH",
        str(BASE_DIR / "Elective Timetable_Trimester II (AY 2026-27) final.xlsx"),
    )
).resolve()
MAPPING_REPORT_PATH = DATA_DIR / "mapping_report.json"

FRONTEND_DIST = BASE_DIR / "frontend" / "dist"

GEMINI_API_KEY = (
    os.getenv("GEMINI_API_KEY")
    or os.getenv("GOOGLE_API_KEY")
    or os.getenv("GOOGLE_GENAI_API_KEY")
)
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
LLM_TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
MAX_ELECTIVES = 4

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

TRIMESTER_LABEL = "Trimester II · AY 2026-27"
