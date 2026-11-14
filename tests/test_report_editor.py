import importlib
import json
import re
import sys

from fastapi.testclient import TestClient


DEMO_PASSWORD = "local-demo-password"


def load_application(monkeypatch, tmp_path):
    monkeypatch.setenv("ANDRABLICKEN_STORAGE", str(tmp_path / "data"))
    monkeypatch.setenv("ANDRABLICKEN_SESSION_SECRET", "r" * 64)
    monkeypatch.setenv("ANDRABLICKEN_ENV", "test")
    monkeypatch.setenv("ANDRABLICKEN_ALLOW_REGISTRATION", "1")
    monkeypatch.setenv("ANDRABLICKEN_SEED_DEMO", "1")
    monkeypatch.setenv("ANDRABLICKEN_DEMO_PASSWORD", DEMO_PASSWORD)
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def csrf_from(response):
    match = re.search(r'name="csrf" value="([^"]+)"', response.text)
    assert match
    return match.group(1)


def login(client, username):
    response = client.post(
        "/login",
        data={"username": username, "password": DEMO_PASSWORD, "csrf": csrf_from(client.get("/login"))},
        follow_redirects=False,
    )
    assert response.status_code == 303


def create_report(client, assignment_id, kind):
    assignment = client.get(f"/assignments/{assignment_id}")
    response = client.post(
        f"/assignments/{assignment_id}/reports",
        data={"csrf": csrf_from(assignment), "kind": kind},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return int(response.headers["location"].split("/reports/", 1)[1].split("/", 1)[0])


def test_club_cannot_open_academy_or_assign_scout(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        assignment = connection.execute(
            "SELECT id FROM assignments WHERE scout_id IS NULL LIMIT 1"
        ).fetchone()
        scout = connection.execute("SELECT id FROM users WHERE role='scout'").fetchone()

    with TestClient(module.app, base_url="http://testserver") as club:
        login(club, "klubb")
        dashboard = club.get("/app")
        assert "Scout Academy" not in dashboard.text
        assert 'href="/courses"' not in dashboard.text
        assert club.get("/courses").status_code == 403
        assert club.get("/courses/lesson/0").status_code == 403
        assert club.get("/courses/quiz").status_code == 403
        detail = club.get(f"/assignments/{assignment['id']}")
        response = club.post(
            f"/assignments/{assignment['id']}/assign/{scout['id']}",
            data={"csrf": csrf_from(detail)},
            follow_redirects=False,
        )
        assert response.status_code == 403

    with module.db() as connection:
        assert connection.execute(
            "SELECT scout_id FROM assignments WHERE id=?", (assignment["id"],)
        ).fetchone()["scout_id"] is None


def test_opposition_editor_matches_pdf_and_saves_chapter_boards(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        assignment_id = connection.execute(
            "SELECT id FROM assignments WHERE scout_id IS NOT NULL LIMIT 1"
        ).fetchone()["id"]

    with TestClient(module.app, base_url="http://testserver") as scout:
        login(scout, "scout")
        report_id = create_report(scout, assignment_id, "opposition")
        editor = scout.get(f"/reports/{report_id}/edit")
        assert "02 — MATCHBILD &amp; LAGUPPSTÄLLNING" in editor.text
        assert "Sammanfattning av matchbilden med exakta minuter" in editor.text
        assert "Utgångsformation" in editor.text
        assert "Uppspelsformation" in editor.text
        assert "Etableringsformation" in editor.text
        assert "3 senaste matchresultaten" in editor.text
        assert "Matchbild före första betydande byte" in editor.text
        assert "Matchbild efter första betydande byte" in editor.text
        assert "Minuten är avgörande" in editor.text
        assert editor.text.count('class="tactic-shell tactics-editor"') == 15

        tactics = {
            "chapter_02": {
                "markers": [
                    {"x": 0.2, "y": 0.3, "team": "a", "number": 1},
                    {"x": 0.8, "y": 0.7, "team": "b", "number": 1},
                    {"x": 0.4, "y": 0.6, "team": "a", "number": 1},
                ],
                "arrows": [{"x1": 0.2, "y1": 0.3, "x2": 0.5, "y2": 0.4, "team": "a"}],
            }
        }
        response = scout.post(
            f"/reports/{report_id}/save",
            data={
                "csrf": csrf_from(editor),
                "game_context": "12:40 – press efter bakåtpass.",
                "recommendation": "Spela förbi första presslinjen.",
                "tactics": json.dumps(tactics),
                "action": "save",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        pdf = scout.get(f"/reports/{report_id}/pdf")
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF-")

    with module.db() as connection:
        payload = json.loads(connection.execute(
            "SELECT payload FROM reports WHERE id=?", (report_id,)
        ).fetchone()["payload"])
    board = json.loads(payload["tactics"])["chapter_02"]
    assert [(marker["team"], marker["number"]) for marker in board["markers"]] == [
        ("a", 1), ("b", 1), ("a", 2)
    ]
    assert len(board["arrows"]) == 1


def test_player_report_asks_how_player_fits_scouted_club(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        assignment_id = connection.execute(
            "SELECT id FROM assignments WHERE scout_id IS NOT NULL LIMIT 1"
        ).fetchone()["id"]

    with TestClient(module.app, base_url="http://testserver") as scout:
        login(scout, "scout")
        report_id = create_report(scout, assignment_id, "player")
        editor = scout.get(f"/reports/{report_id}/edit")
        assert "Passform i laget som scoutingen görs för" in editor.text
        assert 'name="club_fit"' in editor.text
