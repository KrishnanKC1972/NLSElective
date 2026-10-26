from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.excel_ingest import normalize_text, title_similarity
from backend.app.main import app
from backend.app import llm_assistant


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def _course(client: TestClient, title_start: str) -> dict:
    response = client.get("/api/courses")
    assert response.status_code == 200
    for course in response.json():
        if course["title"].lower().startswith(title_start.lower()):
            return course
    raise AssertionError(f"Course not found: {title_start}")


def test_health(client: TestClient):
    payload = client.get("/api/health").json()
    assert payload["status"] == "ok"
    assert payload["courses"] == 74
    assert payload["sessions"] == 335
    assert payload["mapped_sessions"] == 335
    assert payload["unmapped_sessions"] == 0
    assert payload["max_electives"] == 4


def test_catalog_has_sessions(client: TestClient):
    courses = client.get("/api/courses").json()
    assert len(courses) == 74
    scheduled = [course for course in courses if course["has_schedule"]]
    assert len(scheduled) == 73
    non_verbal = _course(client, "Non-Verbal Communication")
    assert non_verbal["schedule_label"]
    assert non_verbal["session_count"] == 4
    assert non_verbal["weekly_minutes"] == 200


def test_empty_selection_is_first_choice_unrestricted(client: TestClient):
    response = client.post(
        "/api/plans/recommendations", json={"selected_ids": []}
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["selected_count"] == 0
    assert payload["summary"]["total_courses"] == 74
    assert payload["summary"]["compatible_count"] == 0
    assert payload["summary"]["clash_count"] == 0
    assert all(
        course["status"] in {"available", "unscheduled"}
        for course in payload["all"]
    )


def test_first_selection_returns_three_sets(client: TestClient):
    first = _course(client, "Non-Verbal Communication")
    response = client.post(
        "/api/plans/recommendations", json={"selected_ids": [first["id"]]}
    )
    assert response.status_code == 200
    payload = response.json()
    summary = payload["summary"]
    assert summary["selected_count"] == 1
    assert summary["clash_count"] > 0
    assert summary["compatible_count"] > 0
    assert (
        summary["clash_count"]
        + summary["compatible_count"]
        + summary["unscheduled_count"]
        + summary["selected_count"]
        == summary["total_courses"]
    )
    assert len(payload["all"]) == 74
    assert len(payload["clash_ids"]) == summary["clash_count"]
    assert len(payload["compatible_ids"]) == summary["compatible_count"]
    clash = next(course for course in payload["all"] if course["status"] == "clash")
    assert clash["clash_count"] >= 1
    assert clash["clashes"][0]["day"]
    assert clash["clashes"][0]["overlap_label"]


def test_second_selection_and_clash_rejection(client: TestClient):
    first = _course(client, "Non-Verbal Communication")
    payload = client.post(
        "/api/plans/recommendations", json={"selected_ids": [first["id"]]}
    ).json()
    compatible_id = payload["compatible_ids"][0]
    clash_id = payload["clash_ids"][0]

    response = client.post(
        "/api/plans/recommendations",
        json={"selected_ids": [first["id"], compatible_id]},
    )
    assert response.status_code == 200
    assert response.json()["summary"]["selected_count"] == 2

    response = client.post(
        "/api/plans/recommendations",
        json={"selected_ids": [first["id"], clash_id]},
    )
    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "clashes with" in detail["message"]


def test_maximum_four_electives(client: TestClient):
    courses = client.get("/api/courses").json()
    scheduled_ids = [course["id"] for course in courses if course["has_schedule"]]
    response = client.post(
        "/api/plans/recommendations",
        json={"selected_ids": scheduled_ids[:5]},
    )
    assert response.status_code == 422


def test_manual_mapping_of_clinic_alias(client: TestClient):
    clinic = _course(client, "Citizenship and Statelessness Clinic")
    assert clinic["has_schedule"] is True
    assert clinic["weekly_minutes"] == 100
    assert clinic["blocks"][0]["day"] == "Friday"


def test_chat_fallback(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    first = _course(client, "Non-Verbal Communication")
    monkeypatch.setattr(llm_assistant.assistant, "_llm", None)
    response = client.post(
        "/api/chat",
        json={
            "message": "Which courses clash with my selection?",
            "selected_ids": [first["id"]],
            "history": [],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "fallback"
    assert payload["answer"]


def test_mapping_report_endpoint(client: TestClient):
    response = client.get("/api/mapping")
    assert response.status_code == 200
    payload = response.json()
    assert payload["counts"]["courses"] == 74
    assert payload["counts"]["mapped_timetable_names"] == 75
    assert payload["counts"]["unmapped_timetable_names"] == 0


def test_matching_helpers():
    assert normalize_text("The Queer Archive, Law & Expressive Cultures") == (
        "the queer archive law and expressive cultures"
    )
    assert title_similarity(
        normalize_text("Law-and-Economics"),
        normalize_text("Twenty | 20 Law-and-Economics"),
    ) > 0.8
