import importlib
import re
import sys

from fastapi.testclient import TestClient


DEMO_PASSWORD = "local-demo-password"


def load_application(monkeypatch, tmp_path):
    monkeypatch.setenv("ANDRABLICKEN_STORAGE", str(tmp_path / "data"))
    monkeypatch.setenv("ANDRABLICKEN_SESSION_SECRET", "w" * 64)
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
    response = client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "csrf": csrf_from(client.get("/login")),
        },
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_complete_assignment_report_review_and_tenant_flow(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        club_id = connection.execute(
            "SELECT id FROM clubs WHERE name='Demo IF'"
        ).fetchone()["id"]
        scout_id = connection.execute(
            "SELECT id FROM users WHERE email='scout@andrablicken.demo'"
        ).fetchone()["id"]

    with TestClient(module.app, base_url="http://testserver") as club:
        login(club, "klubb")
        create_page = club.get("/assignments/new")
        response = club.post(
            "/assignments/new",
            data={
                "csrf": csrf_from(create_page),
                "club_id": str(club_id),
                "title": "Integrationsuppdrag",
                "fixture": "Testlaget – Motståndarna",
                "match_date": "2026-11-10",
                "deadline": "2026-11-20",
                "video_url": "https://example.com/licensed-match",
                "instructions": "Bedöm spelaren med konkreta observationer.",
                "scout_id": str(scout_id),
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assignment_id = int(response.headers["location"].rsplit("/", 1)[1])

        with TestClient(module.app, base_url="http://testserver") as scout:
            login(scout, "scout")
            assignment_page = scout.get(f"/assignments/{assignment_id}")
            assert assignment_page.status_code == 200
            assert "https://example.com/licensed-match" in assignment_page.text
            response = scout.post(
                f"/assignments/{assignment_id}/reports",
                data={"csrf": csrf_from(assignment_page), "kind": "player"},
                follow_redirects=False,
            )
            assert response.status_code == 303
            report_id = int(response.headers["location"].split("/reports/", 1)[1].split("/", 1)[0])

            library = scout.get("/mallbibliotek")
            assert library.status_code == 200
            assert "Spelarrapport" in library.text
            assert "Motståndarrapport" in library.text
            assert "Testlaget – Motståndarna" in library.text
            assert f'action="/reports/{report_id}/attachment"' in library.text
            player_template = scout.get("/static/spelarrapport-mall.pdf")
            opposition_template = scout.get("/static/motstandarrapport-mall.pdf")
            assert player_template.content.startswith(b"%PDF-")
            assert opposition_template.content.startswith(b"%PDF-")
            assert len(player_template.content) > 80_000
            assert len(opposition_template.content) > 90_000

            edit_page = scout.get(f"/reports/{report_id}/edit")
            assert 'id="report-form"' in edit_page.text
            assert 'id="attachment-form"' in edit_page.text
            assert '/static/report-form.js' in edit_page.text
            response = scout.post(
                f"/reports/{report_id}/attachment",
                data={"csrf": csrf_from(library), "return_to": "mallbibliotek"},
                files={"file": ("bilaga.pdf", b"%PDF-1.4\n%%EOF\n", "application/pdf")},
                follow_redirects=False,
            )
            assert response.status_code == 303
            assert response.headers["location"] == "/mallbibliotek"

            edit_page = scout.get(f"/reports/{report_id}/edit")
            response = scout.post(
                f"/reports/{report_id}/save",
                data={
                    "csrf": csrf_from(edit_page),
                    "player_name": "Testspelaren",
                    "game_context": "Konkreta observationer från matchen.",
                    "recommendation": "Följ upp i ytterligare en match.",
                    "tactics": "[]",
                    "action": "submit",
                },
                follow_redirects=False,
            )
            assert response.status_code == 303
            assert scout.get(f"/reports/{report_id}").status_code == 200

        assert club.get(f"/reports/{report_id}").status_code == 403

        with TestClient(module.app, base_url="http://testserver") as admin:
            login(admin, "admin")
            report_page = admin.get(f"/reports/{report_id}")
            assert report_page.status_code == 200
            response = admin.post(
                f"/reports/{report_id}/review",
                data={
                    "csrf": csrf_from(report_page),
                    "decision": "approve",
                    "review_note": "Godkänd i integrationstest.",
                },
                follow_redirects=False,
            )
            assert response.status_code == 303

        approved_report = club.get(f"/reports/{report_id}")
        assert approved_report.status_code == 200
        assert "Godkänd" in approved_report.text
        pdf = club.get(f"/reports/{report_id}/pdf")
        assert pdf.status_code == 200
        assert pdf.headers["content-type"].startswith("application/pdf")
        assert pdf.content.startswith(b"%PDF-")
        attachment = club.get(f"/reports/{report_id}/attachment")
        assert attachment.status_code == 200
        assert attachment.content.startswith(b"%PDF-")
        club_library = club.get("/mallbibliotek")
        assert club_library.status_code == 200
        assert "Klubbkonton kan ladda ner båda mallarna" in club_library.text
        assert 'class="upload-row"' not in club_library.text

    with module.db() as connection:
        connection.execute("INSERT INTO clubs(name) VALUES (?)", ("Rival IF",))
        rival_id = connection.execute(
            "SELECT id FROM clubs WHERE name='Rival IF'"
        ).fetchone()["id"]
        connection.execute(
            "INSERT INTO users(name,username,email,password_hash,role,club_id) VALUES (?,?,?,?,?,?)",
            (
                "Rivalens sportchef",
                "rival",
                "rival@example.test",
                module.password_hash("rival-password"),
                "club",
                rival_id,
            ),
        )

    with TestClient(module.app, base_url="http://testserver") as rival:
        login(rival, "rival", "rival-password")
        assert rival.get(f"/assignments/{assignment_id}").status_code == 403
        assert rival.get(f"/reports/{report_id}").status_code == 403
        assert rival.get(f"/reports/{report_id}/attachment").status_code == 403
