import importlib
import re
import sys

from fastapi.testclient import TestClient


DEMO_PASSWORD = "local-demo-password"


def load_application(monkeypatch, tmp_path):
    monkeypatch.setenv("ANDRABLICKEN_STORAGE", str(tmp_path / "data"))
    monkeypatch.setenv("ANDRABLICKEN_SESSION_SECRET", "p" * 64)
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


def login(client, username, password=DEMO_PASSWORD):
    page = client.get("/login")
    response = client.post(
        "/login",
        data={"username": username, "password": password, "csrf": csrf_from(page)},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_scout_profile_separates_self_reported_and_verified_merits(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        scout_id = connection.execute("SELECT id FROM users WHERE username='scout'").fetchone()["id"]
        assignment = connection.execute(
            "SELECT id FROM assignments WHERE scout_id=? LIMIT 1", (scout_id,)
        ).fetchone()
        now = "2026-11-11T09:30"
        connection.execute(
            "INSERT INTO reports(assignment_id,scout_id,kind,payload,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (assignment["id"], scout_id, "player", '{"recommendation":"Följ upp"}', "approved", now, now),
        )
        report_id = connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]

    with TestClient(module.app, base_url="http://testserver") as scout:
        login(scout, "scout")
        profile = scout.get(f"/scouts/{scout_id}")
        response = scout.post(
            f"/scouts/{scout_id}",
            data={
                "csrf": csrf_from(profile),
                "headline": "Spelaridentifiering och videoanalys",
                "bio": "Bakgrund inom seniorfotboll.",
                "location": "Stockholm / Norden",
                "years_experience": "4",
                "experience": "2024–2026: Matchanalys",
                "merits": "Egen utbildning i opposition scouting",
                "competencies": "Spelaridentifiering\nVideoanalys",
                "languages": "Svenska – modersmål\nEngelska – professionell nivå",
                "availability": "limited",
                "availability_note": "Kvällar och helger",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303

        upload_page = scout.get(f"/scouts/{scout_id}")
        upload = scout.post(
            f"/scouts/{scout_id}/cv",
            data={"csrf": csrf_from(upload_page)},
            files={"file": ("mitt-cv.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")},
            follow_redirects=False,
        )
        assert upload.status_code == 303

        rendered = scout.get(f"/scouts/{scout_id}")
        assert "Självuppgivet" in rendered.text
        assert "Verifierat av Andrablicken" in rendered.text
        assert "Egen utbildning i opposition scouting" in rendered.text
        assert "Spelaridentifiering" in rendered.text
        assert "1 uppdrag · 1 rapport" in rendered.text
        assert f'/reports/{report_id}' in rendered.text

        profile_pdf = scout.get(f"/scouts/{scout_id}/pdf")
        assert profile_pdf.status_code == 200
        assert profile_pdf.headers["content-type"].startswith("application/pdf")
        assert profile_pdf.content.startswith(b"%PDF-")
        cv = scout.get(f"/scouts/{scout_id}/cv")
        assert cv.status_code == 200
        assert cv.content.startswith(b"%PDF-")


def test_profile_and_cv_authorization_preserves_tenant_isolation(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        scout_id = connection.execute("SELECT id FROM users WHERE username='scout'").fetchone()["id"]
        demo_assignment = connection.execute(
            "SELECT id FROM assignments WHERE scout_id=? LIMIT 1", (scout_id,)
        ).fetchone()["id"]
        connection.execute("INSERT INTO clubs(name) VALUES ('Rival IF')")
        rival_club_id = connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        connection.execute(
            "INSERT INTO users(name,username,email,password_hash,role,club_id) VALUES (?,?,?,?,?,?)",
            ("Rival sportchef", "rival", "rival@example.test", module.password_hash("rival-password"), "club", rival_club_id),
        )
        connection.execute(
            "INSERT INTO users(name,username,email,password_hash,role,club_id) VALUES (?,?,?,?,?,NULL)",
            ("Annan scout", "other-scout", "other@example.test", module.password_hash("other-password"), "scout"),
        )
        connection.execute(
            "INSERT INTO scout_profiles(user_id,merits,cv_file,cv_original_name,updated_at) VALUES (?,?,?,?,?)",
            (scout_id, "Självuppgiven merit", "private-cv.pdf", "cv.pdf", "2026-11-11T10:00"),
        )
        now = "2026-11-11T10:00"
        connection.execute(
            "INSERT INTO reports(assignment_id,scout_id,kind,payload,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (demo_assignment, scout_id, "player", "{}", "approved", now, now),
        )
        connection.execute(
            "INSERT INTO assignments(club_id,title,fixture,scout_id,created_at) VALUES (?,?,?,?,?)",
            (rival_club_id, "Rivalens hemliga uppdrag", "Rival – Privat", scout_id, now),
        )
        rival_assignment = connection.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        connection.execute(
            "INSERT INTO reports(assignment_id,scout_id,kind,payload,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?)",
            (rival_assignment, scout_id, "opposition", "{}", "approved", now, now),
        )
    (module.CV_UPLOADS / "private-cv.pdf").write_bytes(b"%PDF-private")

    with TestClient(module.app, base_url="http://testserver") as other_scout:
        login(other_scout, "other-scout", "other-password")
        assert other_scout.get(f"/scouts/{scout_id}").status_code == 403
        account = other_scout.get("/account")
        response = other_scout.post(
            f"/scouts/{scout_id}",
            data={"csrf": csrf_from(account), "headline": "Intrång"},
        )
        assert response.status_code == 403
        assert other_scout.get(f"/scouts/{scout_id}/cv").status_code == 403

    with TestClient(module.app, base_url="http://testserver") as demo_club:
        login(demo_club, "klubb")
        page = demo_club.get(f"/scouts/{scout_id}")
        assert page.status_code == 200
        assert "Självuppgiven merit" in page.text
        assert "Rivalens hemliga uppdrag" not in page.text
        assert demo_club.get(f"/scouts/{scout_id}/cv").status_code == 200

    with TestClient(module.app, base_url="http://testserver") as rival:
        login(rival, "rival", "rival-password")
        page = rival.get(f"/scouts/{scout_id}")
        assert page.status_code == 200
        assert "Rivalens hemliga uppdrag" in page.text
        assert "Pilot: Spelaranalys" not in page.text


def test_cv_upload_rejects_non_pdf(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        scout_id = connection.execute("SELECT id FROM users WHERE username='scout'").fetchone()["id"]
    with TestClient(module.app, base_url="http://testserver") as scout:
        login(scout, "scout")
        page = scout.get(f"/scouts/{scout_id}")
        response = scout.post(
            f"/scouts/{scout_id}/cv",
            data={"csrf": csrf_from(page)},
            files={"file": ("cv.pdf", b"not a pdf", "application/pdf")},
        )
        assert response.status_code == 400
