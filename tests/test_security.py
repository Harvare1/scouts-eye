import importlib
import re
import sys

import pytest
from fastapi.testclient import TestClient


def load_application(monkeypatch, tmp_path, *, production=False):
    monkeypatch.setenv("ANDRABLICKEN_STORAGE", str(tmp_path / "data"))
    monkeypatch.setenv("ANDRABLICKEN_SESSION_SECRET", "s" * 64)
    monkeypatch.setenv("ANDRABLICKEN_ENV", "production" if production else "test")
    monkeypatch.setenv("ANDRABLICKEN_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("ANDRABLICKEN_ALLOW_REGISTRATION", "0" if production else "1")
    monkeypatch.setenv("ANDRABLICKEN_SEED_DEMO", "0" if production else "1")
    if not production:
        monkeypatch.setenv("ANDRABLICKEN_DEMO_PASSWORD", "local-demo-password")
    if production:
        monkeypatch.setenv("ANDRABLICKEN_BOOTSTRAP_ADMIN_EMAIL", "admin@example.test")
        monkeypatch.setenv("ANDRABLICKEN_BOOTSTRAP_ADMIN_PASSWORD", "a-secure-bootstrap-password")
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def csrf_from(response):
    match = re.search(r'name="csrf" value="([^"]+)"', response.text)
    assert match
    return match.group(1)


def login(client, email, password):
    page = client.get("/login")
    response = client.post(
        "/login",
        data={"email": email, "password": password, "csrf": csrf_from(page)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response


def test_production_bootstraps_only_admin_and_disables_registration(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path, production=True)
    with module.db() as connection:
        users = connection.execute("SELECT email, role FROM users").fetchall()

    assert [(user["email"], user["role"]) for user in users] == [
        ("admin@example.test", "admin")
    ]

    with TestClient(module.app, base_url="https://testserver") as client:
        assert client.get("/register").status_code == 404
        response = login(client, "admin@example.test", "a-secure-bootstrap-password")
        assert "secure" in response.headers["set-cookie"].lower()
        assert client.get("/health").json() == {"status": "ok", "mode": "production"}


def test_other_scout_cannot_open_assigned_task_by_guessing_url(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        assignment = connection.execute(
            "SELECT id FROM assignments WHERE scout_id IS NOT NULL LIMIT 1"
        ).fetchone()
        connection.execute(
            "INSERT INTO users(name,email,password_hash,role,club_id) VALUES (?,?,?,?,NULL)",
            ("Annan scout", "other-scout@example.test", module.password_hash("another-password"), "scout"),
        )

    with TestClient(module.app, base_url="http://testserver") as client:
        login(client, "other-scout@example.test", "another-password")
        assert client.get(f"/assignments/{assignment['id']}").status_code == 403


def test_other_club_cannot_open_approved_report_or_attachment(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        connection.execute("INSERT INTO clubs(name) VALUES (?)", ("Annan IF",))
        other_club_id = connection.execute(
            "SELECT id FROM clubs WHERE name=?", ("Annan IF",)
        ).fetchone()["id"]
        connection.execute(
            "INSERT INTO users(name,email,password_hash,role,club_id) VALUES (?,?,?,?,?)",
            (
                "Annan sportchef",
                "other-club@example.test",
                module.password_hash("another-password"),
                "club",
                other_club_id,
            ),
        )
        assignment = connection.execute(
            "SELECT id, scout_id FROM assignments WHERE scout_id IS NOT NULL LIMIT 1"
        ).fetchone()
        now = "2026-11-09T12:00"
        connection.execute(
            "INSERT INTO reports(assignment_id,scout_id,kind,payload,status,created_at,updated_at,uploaded_file) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (assignment["id"], assignment["scout_id"], "player", "{}", "approved", now, now, "private.pdf"),
        )
        report_id = connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        (module.UPLOADS / "private.pdf").write_bytes(b"%PDF-private")

    with TestClient(module.app, base_url="http://testserver") as client:
        login(client, "other-club@example.test", "another-password")
        assert client.get(f"/reports/{report_id}").status_code == 403
        assert client.get(f"/reports/{report_id}/attachment").status_code == 403


def test_production_requires_explicit_session_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("ANDRABLICKEN_ENV", "production")
    monkeypatch.setenv("ANDRABLICKEN_STORAGE", str(tmp_path / "data"))
    monkeypatch.delenv("ANDRABLICKEN_SESSION_SECRET", raising=False)
    sys.modules.pop("app", None)

    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        importlib.import_module("app")
