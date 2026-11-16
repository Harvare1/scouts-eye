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
    monkeypatch.setenv("ANDRABLICKEN_BOOTSTRAP_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ANDRABLICKEN_BOOTSTRAP_ADMIN_EMAIL", "admin@example.test")
    monkeypatch.setenv("ANDRABLICKEN_BOOTSTRAP_ADMIN_PASSWORD", ADMIN_PASSWORD)
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def csrf_from(response):
    match = re.search(r'name="csrf" value="([^"]+)"', response.text)
    assert match
    return match.group(1)


def login(client, username, password):
    response = client.post(
        "/login",
        data={
            "username": username,
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
        assert login(admin, "admin", ADMIN_PASSWORD).status_code == 303
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
                "username": "short-user",
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
                "username": "test-scout",
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
                "username": "pilot-club",
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
            assert login(scout, "test-scout", SCOUT_PASSWORD).status_code == 303
            assert scout.get("/app").status_code == 200
            assert scout.get("/admin/users").status_code == 403

            with TestClient(module.app, base_url="https://testserver") as email_client:
                email_login = login(email_client, "scout@example.test", SCOUT_PASSWORD)
                assert email_login.status_code == 200
                assert "Fel användarnamn eller lösenord" in email_login.text

            response = admin_post(admin, f"/admin/users/{scout_id}/status", {"action": "deactivate"})
            assert response.status_code == 303
            assert scout.get("/app").status_code == 401

        with TestClient(module.app, base_url="https://testserver") as inactive:
            response = login(inactive, "test-scout", SCOUT_PASSWORD)
            assert response.status_code == 200
            assert "Kontot är avstängt" in response.text

        assert admin_post(admin, f"/admin/users/{scout_id}/status", {"action": "activate"}).status_code == 303
        assert admin_post(
            admin,
            f"/admin/users/{scout_id}/password",
            {"password": RESET_PASSWORD, "confirm_password": RESET_PASSWORD},
        ).status_code == 303

        with TestClient(module.app, base_url="https://testserver") as changed:
            assert login(changed, "test-scout", SCOUT_PASSWORD).status_code == 200
            assert login(changed, "test-scout", RESET_PASSWORD).status_code == 303
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
            assert login(final_login, "test-scout", RESET_PASSWORD).status_code == 200
            assert login(final_login, "test-scout", FINAL_PASSWORD).status_code == 303

        response = admin_post(
            admin,
            f"/admin/users/{club_user_id}/update",
            {
                "name": "Pilotens sportchef",
                "username": "pilot-club",
                "email": "club@example.test",
                "role": "club",
                "club_id": str(other_id),
            },
        )
        assert response.status_code == 303
        with module.db() as connection:
            assert connection.execute("SELECT club_id FROM users WHERE id=?", (club_user_id,)).fetchone()["club_id"] == other_id

        duplicate = admin_post(
            admin,
            f"/admin/users/{club_user_id}/update",
            {
                "name": "Pilotens sportchef",
                "username": "TEST-SCOUT",
                "email": "club@example.test",
                "role": "club",
                "club_id": str(other_id),
            },
        )
        assert duplicate.status_code == 303
        with module.db() as connection:
            assert connection.execute("SELECT username FROM users WHERE id=?", (club_user_id,)).fetchone()["username"] == "pilot-club"

        response = admin_post(admin, f"/admin/users/{admin_id}/status", {"action": "deactivate"})
        assert response.status_code == 303
        with module.db() as connection:
            assert connection.execute("SELECT active FROM users WHERE id=?", (admin_id,)).fetchone()["active"] == 1


def test_admin_edits_clubs_and_linked_account_data_safely(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with TestClient(module.app, base_url="https://testserver") as admin:
        assert login(admin, "admin", ADMIN_PASSWORD).status_code == 303
        assert admin_post(admin, "/admin/clubs", {"name": "Pilot IF"}).status_code == 303
        assert admin_post(admin, "/admin/clubs", {"name": "Andra IF"}).status_code == 303

        with module.db() as connection:
            pilot_id = connection.execute("SELECT id FROM clubs WHERE name='Pilot IF'").fetchone()["id"]
            other_id = connection.execute("SELECT id FROM clubs WHERE name='Andra IF'").fetchone()["id"]
            connection.execute("INSERT INTO clubs(name) VALUES ('Andrablicken Academy')")
            academy_id = connection.execute("SELECT id FROM clubs WHERE name='Andrablicken Academy'").fetchone()["id"]
            connection.execute(
                "INSERT INTO users(name,username,email,password_hash,role,club_id) VALUES (?,?,?,?,?,?)",
                ("Klubbansvarig", "klubbansvarig", "klubb@example.test", module.password_hash(SCOUT_PASSWORD), "club", pilot_id),
            )
            club_user_id = connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
            connection.execute(
                "INSERT INTO assignments(club_id,title,fixture,created_at) VALUES (?,?,?,?)",
                (pilot_id, "Pilotuppdrag", "Pilot IF – Exempel FF", "2026-11-16T12:00"),
            )
            assignment_id = connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

        with TestClient(module.app, base_url="https://testserver") as club_client:
            assert login(club_client, "klubbansvarig", SCOUT_PASSWORD).status_code == 303

            response = admin_post(
                admin,
                f"/admin/users/{club_user_id}/update",
                {
                    "name": "Ny klubbansvarig",
                    "username": "ny-klubbansvarig",
                    "email": "ny.klubb@example.test",
                    "role": "club",
                    "club_id": str(pilot_id),
                },
            )
            assert response.status_code == 303
            assert club_client.get("/app").status_code == 401

            with module.db() as connection:
                account = connection.execute("SELECT * FROM users WHERE id=?", (club_user_id,)).fetchone()
                assert account["name"] == "Ny klubbansvarig"
                assert account["username"] == "ny-klubbansvarig"
                assert account["email"] == "ny.klubb@example.test"
                assert account["club_id"] == pilot_id

            assert admin_post(admin, f"/admin/clubs/{pilot_id}/update", {"name": "Pilot FK"}).status_code == 303
            with module.db() as connection:
                assert connection.execute("SELECT name FROM clubs WHERE id=?", (pilot_id,)).fetchone()["name"] == "Pilot FK"
                assert connection.execute("SELECT club_id FROM users WHERE id=?", (club_user_id,)).fetchone()["club_id"] == pilot_id
                assert connection.execute("SELECT club_id FROM assignments WHERE id=?", (assignment_id,)).fetchone()["club_id"] == pilot_id

            page = admin.get("/admin/users")
            assert "Pilot FK" in page.text
            assert "1 aktiva av 1 konton · 1 uppdrag" in page.text
            assert "Ny klubbansvarig" in page.text

            assert admin_post(admin, f"/admin/clubs/{pilot_id}/update", {"name": "andra if"}).status_code == 303
            assert admin_post(admin, f"/admin/clubs/{academy_id}/update", {"name": "Nytt Academy-namn"}).status_code == 303
            with module.db() as connection:
                assert connection.execute("SELECT name FROM clubs WHERE id=?", (pilot_id,)).fetchone()["name"] == "Pilot FK"
                assert connection.execute("SELECT name FROM clubs WHERE id=?", (academy_id,)).fetchone()["name"] == "Andrablicken Academy"

            crafted = admin_post(
                admin,
                f"/admin/users/{club_user_id}/update",
                {
                    "name": "Ny klubbansvarig",
                    "username": "ny-klubbansvarig",
                    "email": "ny.klubb@example.test",
                    "role": "club",
                    "club_id": str(academy_id),
                },
            )
            assert crafted.status_code == 303
            with module.db() as connection:
                assert connection.execute("SELECT club_id FROM users WHERE id=?", (club_user_id,)).fetchone()["club_id"] == pilot_id

            assert login(club_client, "ny-klubbansvarig", SCOUT_PASSWORD).status_code == 303
            account_page = club_client.get("/account")
            forbidden = club_client.post(
                f"/admin/clubs/{other_id}/update",
                data={"name": "Otillåtet namn", "csrf": csrf_from(account_page)},
                follow_redirects=False,
            )
            assert forbidden.status_code == 403
