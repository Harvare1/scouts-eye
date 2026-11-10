import importlib
import re
import sqlite3
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
        monkeypatch.setenv("ANDRABLICKEN_BOOTSTRAP_ADMIN_USERNAME", "admin")
        monkeypatch.setenv("ANDRABLICKEN_BOOTSTRAP_ADMIN_EMAIL", "admin@example.test")
        monkeypatch.setenv("ANDRABLICKEN_BOOTSTRAP_ADMIN_PASSWORD", "a-secure-bootstrap-password")
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def csrf_from(response):
    match = re.search(r'name="csrf" value="([^"]+)"', response.text)
    assert match
    return match.group(1)


def login(client, username, password):
    page = client.get("/login")
    response = client.post(
        "/login",
        data={"username": username, "password": password, "csrf": csrf_from(page)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    return response


def test_production_bootstraps_only_admin_and_disables_registration(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path, production=True)
    with module.db() as connection:
        users = connection.execute("SELECT username, email, role FROM users").fetchall()

    assert [(user["username"], user["email"], user["role"]) for user in users] == [
        ("admin", "admin@example.test", "admin")
    ]

    with TestClient(module.app, base_url="https://testserver") as client:
        assert client.get("/register").status_code == 404
        response = login(client, "admin", "a-secure-bootstrap-password")
        assert "secure" in response.headers["set-cookie"].lower()
        assert client.get("/health").json() == {"status": "ok", "mode": "production"}


def test_other_scout_cannot_open_assigned_task_by_guessing_url(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        assignment = connection.execute(
            "SELECT id FROM assignments WHERE scout_id IS NOT NULL LIMIT 1"
        ).fetchone()
        connection.execute(
            "INSERT INTO users(name,username,email,password_hash,role,club_id) VALUES (?,?,?,?,?,NULL)",
            ("Annan scout", "other-scout", "other-scout@example.test", module.password_hash("another-password"), "scout"),
        )

    with TestClient(module.app, base_url="http://testserver") as client:
        login(client, "other-scout", "another-password")
        assert client.get(f"/assignments/{assignment['id']}").status_code == 403


def test_other_club_cannot_open_approved_report_or_attachment(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        connection.execute("INSERT INTO clubs(name) VALUES (?)", ("Annan IF",))
        other_club_id = connection.execute(
            "SELECT id FROM clubs WHERE name=?", ("Annan IF",)
        ).fetchone()["id"]
        connection.execute(
            "INSERT INTO users(name,username,email,password_hash,role,club_id) VALUES (?,?,?,?,?,?)",
            (
                "Annan sportchef",
                "other-club",
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
        login(client, "other-club", "another-password")
        assert client.get(f"/reports/{report_id}").status_code == 403
        assert client.get(f"/reports/{report_id}/attachment").status_code == 403


def test_production_requires_explicit_session_secret(monkeypatch, tmp_path):
    monkeypatch.setenv("ANDRABLICKEN_ENV", "production")
    monkeypatch.setenv("ANDRABLICKEN_STORAGE", str(tmp_path / "data"))
    monkeypatch.delenv("ANDRABLICKEN_SESSION_SECRET", raising=False)
    sys.modules.pop("app", None)

    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        importlib.import_module("app")


def test_legacy_accounts_receive_unique_usernames(monkeypatch, tmp_path):
    storage = tmp_path / "data"
    storage.mkdir()
    connection = sqlite3.connect(storage / "portal.sqlite3")
    connection.executescript(
        """
        CREATE TABLE clubs(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
        CREATE TABLE users(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            club_id INTEGER REFERENCES clubs(id)
        );
        INSERT INTO users(name,email,password_hash,role,club_id)
        VALUES ('Malte Ett','malte@example.test','legacy','admin',NULL);
        INSERT INTO users(name,email,password_hash,role,club_id)
        VALUES ('Malte Två','malte@other.test','legacy','scout',NULL);
        """
    )
    connection.close()

    monkeypatch.setenv("ANDRABLICKEN_STORAGE", str(storage))
    monkeypatch.setenv("ANDRABLICKEN_SESSION_SECRET", "m" * 64)
    monkeypatch.setenv("ANDRABLICKEN_ENV", "test")
    monkeypatch.setenv("ANDRABLICKEN_ALLOW_REGISTRATION", "0")
    monkeypatch.setenv("ANDRABLICKEN_SEED_DEMO", "0")
    sys.modules.pop("app", None)
    module = importlib.import_module("app")

    with module.db() as migrated:
        users = migrated.execute("SELECT username,email FROM users ORDER BY id").fetchall()
        indexes = migrated.execute("PRAGMA index_list(users)").fetchall()

    assert [(user["username"], user["email"]) for user in users] == [
        ("malte", "malte@example.test"),
        ("malte-2", "malte@other.test"),
    ]
    assert any(index["name"] == "users_username_nocase" and index["unique"] for index in indexes)
