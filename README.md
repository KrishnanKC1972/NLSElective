# NLS Elective Planner

A full-stack elective planning tool for the Trimester II (AY 2026-27) elective list. It maps catalogue titles to timetable course names, detects timetable clashes, builds a weekly calendar, and includes **Lex**, a Gemini-powered planning assistant with a deterministic fallback.

## Features

- 74 catalogue electives mapped against the timetable workbook.
- Select up to **four** electives. The first pick is unrestricted; later picks must be clash-free.
- Three catalogue views after selection: **All**, **Compatible**, and **Clashes**.
- Weekly calendar (Monday-Saturday, 9:00 AM-7:00 PM) with colour-coded class blocks.
- Credits, weekly contact time, active days, and per-day load summary.
- Search by title, faculty, concentration, day, or cohort; filter by credits.
- Course detail view with all published slots, rooms, audience, and clash details.
- Lex chat assistant grounded in the catalogue and current planner state.
- SQLite persistence and a JSON mapping audit report.

## Stack

- **Backend:** FastAPI, SQLAlchemy, SQLite, openpyxl
- **Frontend:** React 19, TypeScript, Vite
- **Assistant:** `langchain-google-genai` / Gemini, with a rules-based fallback
- **Data:** `Elective List.xlsx` and `Elective Timetable_Trimester II (AY 2026-27) final.xlsx`

## Quick start

### 1. Python environment

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Environment variables

Create `.env` in the project root:

```dotenv
# Optional. Without a key, Lex uses the deterministic fallback.
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini-2.5-flash
TEMPERATURE=0.2
```

Optional overrides: `SQLITE_PATH`, `ELECTIVE_LIST_PATH`, `TIMETABLE_PATH`, `ALLOWED_ORIGINS`.

### 3. Build the database

```powershell
.\venv\Scripts\python.exe -m backend.scripts.ingest
```

This reads both workbooks, rebuilds `data/electives.db`, and writes `data/mapping_report.json`.
The API also runs ingestion automatically if the database is empty.

### 4. Build the frontend

```powershell
cd frontend
npm install
npm run build
```

### 5. Run the app

```powershell
cd ..
.\venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Open <http://127.0.0.1:8000>. When `frontend/dist` exists, FastAPI serves the built React app.

For frontend development:

```powershell
cd frontend
npm run dev
```

Vite runs on <http://127.0.0.1:5173> and proxies `/api` to FastAPI on port 8000.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Database counts and assistant status |
| `GET` | `/api/courses` | Full catalogue with sessions and weekly blocks |
| `POST` | `/api/plans/recommendations` | Planner state for `{ "selected_ids": [...] }` |
| `POST` | `/api/chat` | Ask Lex a question with current selection and history |
| `GET` | `/api/mapping` | Mapping audit report |
| `GET` | `/docs` | OpenAPI documentation |

## Planning rules

- A later elective clashes when it shares a weekday and has **strictly overlapping minutes** with a selected course. Adjacent periods do not clash.
- Periods separated by up to 15 minutes are merged for calendar display, while weekly contact time counts published class periods.
- Courses with multiple published timetable rows show **all** listed slots. Section allocation is not modelled; confirm section choices with the academic office.
- `Regulatory Governance: Local to Global` has no published timetable and is included as `No timetable`. It does not block other picks.

## Data mapping

Ingestion uses exact title matching, then fuzzy matching, then a small manual alias list. The current report records 75 timetable names mapped to 74 catalogue courses. Manual aliases include:

- `Law and Economics` / `Twenty Law and Economics` -> `Twenty | 20 Law-and-Economics`
- `Citizenship and Immigration` -> `Citizenship and Statelessness Clinic- II (Drafting and Research)`

## Tests

```powershell
.\venv\Scripts\python.exe -m pytest backend\tests -q
```

The suite covers time parsing, block merging, clash detection, API contracts, mapping counts, selection limits, and the fallback assistant.

## Project layout

```text
backend/
  app/          FastAPI app, ingestion, scheduling, planner, schemas, LLM
  scripts/      Ingestion CLI
  tests/        Pytest suite
data/           SQLite database and mapping report
frontend/       React + TypeScript + Vite interface
```

## Disclaimer

This tool is for planning only. It is not official registration. Verify elective availability, section allocation, and timetable changes with the academic office.
