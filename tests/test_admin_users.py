import importlib
import re
import sys

from fastapi.testclient import TestClient


ADMIN_PASSWORD = "adm123"
SCOUT_PASSWORD = "sct123"
RESET_PASSWORD = "rst456"
FINAL_PASSWORD = "fin789"


def load_application(monkeypatch, tmp_path):
    monkeypatch.setenv("ANDRABLICKEN_STORAGE", str(tmp_path / "data"))
    monkeypatch.setenv("ANDRABLICKEN_SESSION_SECRET", "a" * 64)
    monkeypatch.setenv("ANDRABLICKEN_ENV", "production")
    monkeypatch.setenv("ANDRABLICKEN_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("ANDRABLICKEN_ALLOW_REGISTRATION", "0")
    monkeypatch.setenv("ANDRABLICKEN_SEED_DEMO", "0")
    monkeypatch.setenv("ANDRABLICKEN_BOOTSTRAP_ADMIN_EMAIL", "admin@example.test")
    monkeypatch.setenv("ANDRABLICKEN_BOOTSTRAP_ADMIN_PASSWORD", ADMIN_PASSWORD)
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def csrf_from(response):
    match = re.search(r'name="csrf" value="([^"]+)"', response.text)
    assert match
    return match.group(1)


def login(client, email, password):
    response = client.post(
        "/login",
        data={
            "email": email,
            "password": password,
            "csrf": csrf_from(client.get("/login")),
        },
        follow_redirects=False,
    )
    return response


def admin_post(client, path, data):
    page = client.get("/admin/users")
    assert page.status_code == 200
    return client.post(
        path,
        data={"csrf": csrf_from(page), **data},
        follow_redirects=False,
    )


def test_admin_can_manage_accounts_and_sessions(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with TestClient(module.app, base_url="https://testserver") as admin:
        assert login(admin, "admin@example.test", ADMIN_PASSWORD).status_code == 303
        users_page = admin.get("/admin/users")
        assert users_page.status_code == 200
        assert "KLUBBAR & KONTON" in users_page.text
        assert 'minlength="6"' in users_page.text

        response = admin_post(admin, "/admin/clubs", {"name": "Pilot IF"})
        assert response.status_code == 303
        response = admin_post(admin, "/admin/clubs", {"name": "Andra IF"})
        assert response.status_code == 303
        with module.db() as connection:
            pilot_id = connection.execute("SELECT id FROM clubs WHERE name='Pilot IF'").fetchone()["id"]
            other_id = connection.execute("SELECT id FROM clubs WHERE name='Andra IF'").fetchone()["id"]

        response = admin_post(
            admin,
            "/admin/users",
            {
                "name": "För kort lösenord",
                "email": "short@example.test",
                "role": "scout",
                "club_id": "",
                "password": "12345",
                "confirm_password": "12345",
            },
        )
        assert response.status_code == 303
        with module.db() as connection:
            assert connection.execute("SELECT 1 FROM users WHERE email='short@example.test'").fetchone() is None

        response = admin_post(
            admin,
            "/admin/users",
            {
                "name": "Test Scout",
                "email": "scout@example.test",
                "role": "scout",
                "club_id": "",
                "password": SCOUT_PASSWORD,
                "confirm_password": SCOUT_PASSWORD,
            },
        )
        assert response.status_code == 303
        response = admin_post(
            admin,
            "/admin/users",
            {
                "name": "Pilotens sportchef",
                "email": "club@example.test",
                "role": "club",
                "club_id": str(pilot_id),
                "password": SCOUT_PASSWORD,
                "confirm_password": SCOUT_PASSWORD,
            },
        )
        assert response.status_code == 303
        with module.db() as connection:
            scout_id = connection.execute("SELECT id FROM users WHERE email='scout@example.test'").fetchone()["id"]
            club_user_id = connection.execute("SELECT id FROM users WHERE email='club@example.test'").fetchone()["id"]
            admin_id = connection.execute("SELECT id FROM users WHERE email='admin@example.test'").fetchone()["id"]

        with TestClient(module.app, base_url="https://testserver") as scout:
            assert login(scout, "scout@example.test", SCOUT_PASSWORD).status_code == 303
            assert scout.get("/app").status_code == 200
            assert scout.get("/admin/users").status_code == 403

            response = admin_post(admin, f"/admin/users/{scout_id}/status", {"action": "deactivate"})
            assert response.status_code == 303
            assert scout.get("/app").status_code == 401

        with TestClient(module.app, base_url="https://testserver") as inactive:
            response = login(inactive, "scout@example.test", SCOUT_PASSWORD)
            assert response.status_code == 200
            assert "Kontot är avstängt" in response.text

        assert admin_post(admin, f"/admin/users/{scout_id}/status", {"action": "activate"}).status_code == 303
        assert admin_post(
            admin,
            f"/admin/users/{scout_id}/password",
            {"password": RESET_PASSWORD, "confirm_password": RESET_PASSWORD},
        ).status_code == 303

        with TestClient(module.app, base_url="https://testserver") as changed:
            assert login(changed, "scout@example.test", SCOUT_PASSWORD).status_code == 200
            assert login(changed, "scout@example.test", RESET_PASSWORD).status_code == 303
            account = changed.get("/account")
            response = changed.post(
                "/account/password",
                data={
                    "csrf": csrf_from(account),
                    "current_password": RESET_PASSWORD,
                    "new_password": FINAL_PASSWORD,
                    "confirm_password": FINAL_PASSWORD,
                },
                follow_redirects=False,
            )
            assert response.status_code == 303
            assert changed.get("/app").status_code == 200

        with TestClient(module.app, base_url="https://testserver") as final_login:
            assert login(final_login, "scout@example.test", RESET_PASSWORD).status_code == 200
            assert login(final_login, "scout@example.test", FINAL_PASSWORD).status_code == 303

        response = admin_post(
            admin,
            f"/admin/users/{club_user_id}/update",
            {
                "name": "Pilotens sportchef",
                "email": "club@example.test",
                "role": "club",
                "club_id": str(other_id),
            },
        )
        assert response.status_code == 303
        with module.db() as connection:
            assert connection.execute("SELECT club_id FROM users WHERE id=?", (club_user_id,)).fetchone()["club_id"] == other_id

        response = admin_post(admin, f"/admin/users/{admin_id}/status", {"action": "deactivate"})
        assert response.status_code == 303
        with module.db() as connection:
            assert connection.execute("SELECT active FROM users WHERE id=?", (admin_id,)).fetchone()["active"] == 1
