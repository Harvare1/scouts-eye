import importlib
import json
import re
import sys

from fastapi.testclient import TestClient


PASSWORD = "local-demo-password"


def load_application(monkeypatch, tmp_path):
    monkeypatch.setenv("ANDRABLICKEN_STORAGE", str(tmp_path / "data"))
    monkeypatch.setenv("ANDRABLICKEN_SESSION_SECRET", "a" * 64)
    monkeypatch.setenv("ANDRABLICKEN_ENV", "test")
    monkeypatch.setenv("ANDRABLICKEN_ALLOW_REGISTRATION", "1")
    monkeypatch.setenv("ANDRABLICKEN_SEED_DEMO", "1")
    monkeypatch.setenv("ANDRABLICKEN_DEMO_PASSWORD", PASSWORD)
    sys.modules.pop("app", None)
    return importlib.import_module("app")


def csrf_from(response):
    match = re.search(r'name="csrf" value="([^"]+)"', response.text)
    assert match
    return match.group(1)


def login(client, username):
    response = client.post(
        "/login",
        data={"username": username, "password": PASSWORD, "csrf": csrf_from(client.get("/login"))},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_academy_seeds_six_lesson_draft_and_locked_advanced_courses(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        courses = connection.execute(
            "SELECT id,slug,access_type,status,price_ore,study_time_label FROM academy_courses ORDER BY id"
        ).fetchall()
        intro_id = connection.execute(
            "SELECT id FROM academy_courses WHERE slug='introduktion-fotbollsscouting'"
        ).fetchone()["id"]
        lesson_count = connection.execute(
            "SELECT COUNT(*) AS c FROM academy_lessons l JOIN academy_modules m ON m.id=l.module_id WHERE m.course_id=?",
            (intro_id,),
        ).fetchone()["c"]
        quiz_count = connection.execute(
            "SELECT COUNT(*) AS c FROM academy_quiz_questions WHERE course_id=?", (intro_id,)
        ).fetchone()["c"]

    assert [course["slug"] for course in courses] == [
        "introduktion-fotbollsscouting",
        "spelaridentifiering-rekrytering",
        "motstandaranalys-taktisk-scouting",
    ]
    assert all(course["status"] == "draft" for course in courses)
    assert courses[0]["access_type"] == "free" and courses[0]["price_ore"] == 0
    assert courses[0]["study_time_label"] == "2–3 timmar"
    assert all(course["access_type"] == "paid" and course["price_ore"] > 0 for course in courses[1:])
    assert all(course["study_time_label"] == "5–7 timmar" for course in courses[1:])
    assert lesson_count == 6
    assert quiz_count == 10

    with TestClient(module.app, base_url="http://testserver") as scout:
        login(scout, "scout")
        catalog = scout.get("/courses")
        assert "INTRODUKTION TILL FOTBOLLSSCOUTING" in catalog.text
        assert "SPELARIDENTIFIERING OCH REKRYTERING" in catalog.text
        assert "Öppen för anmälan" in catalog.text
        assert "Kommer snart" in catalog.text
        assert "Så ska den betalda kursen se ut senare" not in catalog.text
        assert "kvalitetssäkringsutkast" not in catalog.text.lower()
        assert "Status: in_progress" not in catalog.text
        advanced = scout.get("/courses/spelaridentifiering-rekrytering")
        assert "Kursen öppnar längre fram" in advanced.text
        assert "Hur klubbens spelidé, behov och ekonomiska förutsättningar" in advanced.text
        assert "Planerat originalinnehåll" not in advanced.text
        response = scout.post(
            f"/courses/{courses[1]['id']}/enroll",
            data={"csrf": csrf_from(advanced)},
            follow_redirects=False,
        )
        assert response.status_code == 409

    with TestClient(module.app, base_url="http://testserver") as club:
        login(club, "klubb")
        assert club.get("/courses").status_code == 403


def test_full_academy_progress_quiz_examination_and_certificate(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        course = connection.execute(
            "SELECT * FROM academy_courses WHERE slug='introduktion-fotbollsscouting'"
        ).fetchone()
        lessons = connection.execute(
            "SELECT l.id,q.correct_index FROM academy_lessons l JOIN academy_modules m ON m.id=l.module_id JOIN academy_lesson_questions q ON q.lesson_id=l.id WHERE m.course_id=? ORDER BY l.position",
            (course["id"],),
        ).fetchall()
        questions = connection.execute(
            "SELECT id,correct_index FROM academy_quiz_questions WHERE course_id=? ORDER BY position",
            (course["id"],),
        ).fetchall()
        scout_id = connection.execute("SELECT id FROM users WHERE username='scout'").fetchone()["id"]

    with TestClient(module.app, base_url="http://testserver") as scout:
        login(scout, "scout")
        detail = scout.get("/courses/introduktion-fotbollsscouting")
        response = scout.post(
            f"/courses/{course['id']}/enroll",
            data={"csrf": csrf_from(detail)},
            follow_redirects=False,
        )
        assert response.status_code == 303
        detail = scout.get(response.headers["location"])
        csrf = csrf_from(detail)

        first = scout.post(
            f"/api/academy/lessons/{lessons[0]['id']}/progress",
            headers={"X-CSRF-Token": csrf},
            json={"reflection": "Tre relevanta frågor till sportchefen.", "answer_index": 0},
        )
        assert first.status_code == 200
        assert first.json()["completed"] is False
        assert first.json()["explanation"]

        for lesson in lessons:
            response = scout.post(
                f"/api/academy/lessons/{lesson['id']}/progress",
                headers={"X-CSRF-Token": csrf},
                json={
                    "reflection": "Ett konkret reflektionssvar med matchkontext och tidsstämpel.",
                    "answer_index": lesson["correct_index"],
                },
            )
            assert response.status_code == 200
            assert response.json()["correct"] is True
            assert response.json()["completed"] is True

        quiz_page = scout.get(f"/courses/{course['id']}/quiz")
        assert quiz_page.status_code == 200
        quiz_data = {"csrf": csrf_from(quiz_page)}
        quiz_data.update({f"q{question['id']}": str(question["correct_index"]) for question in questions})
        quiz_result = scout.post(f"/courses/{course['id']}/quiz", data=quiz_data)
        assert quiz_result.status_code == 200
        assert "10 / 10" in quiz_result.text
        assert "Svar och förklaringar" in quiz_result.text

        detail = scout.get("/courses/introduktion-fotbollsscouting")
        exam_start = scout.post(
            f"/courses/{course['id']}/examination/start",
            data={"csrf": csrf_from(detail), "kind": "opposition"},
            follow_redirects=False,
        )
        assert exam_start.status_code == 303
        report_id = int(exam_start.headers["location"].split("/reports/", 1)[1].split("/", 1)[0])
        editor = scout.get(exam_start.headers["location"])
        blocked = scout.post(
            f"/reports/{report_id}/save",
            data={
                "csrf": csrf_from(editor),
                "game_context": "12:40 – konkret matchobservation.",
                "observations": "12:40, 25:10, 38:20, 55:00 och 71:30 – fem avgränsade situationer.",
                "strengths": "Två tydliga styrkor.",
                "weaknesses": "Två tydliga begränsningar.",
                "recommendation": "Konkret rekommendation med redovisad osäkerhet.",
                "limitations": "En match och begränsat observationsunderlag.",
                "tactics": "{}",
                "action": "submit",
            },
            follow_redirects=False,
        )
        assert blocked.status_code == 303
        blocked_editor = scout.get(blocked.headers["location"])
        assert "minst två styrkor" in blocked_editor.text.lower()
        valid_exam_data = {
            "game_context": "12:40 – konkret matchobservation.",
            "observations": "12:40 – press.\n25:10 – uppspel.\n38:20 – omställning.\n55:00 – fast situation.\n71:30 – lågt block.",
            "strengths": "1. Hög press med korta avstånd.\n2. Hotar ytan bakom ytterbacken.",
            "weaknesses": "1. Lämnar yta bakom högerbacken.\n2. Svagt skydd vid defensiv omställning.",
            "recommendation": "Spela snabbt bakom högerbacken efter bollvinst.",
            "limitations": "Analysen bygger på en match och behöver bekräftas med ytterligare observationer.",
            "tactics": "{}",
            "action": "submit",
        }
        submit = scout.post(
            f"/reports/{report_id}/save",
            data={"csrf": csrf_from(blocked_editor), **valid_exam_data},
            follow_redirects=False,
        )
        assert submit.status_code == 303
        assert scout.get("/app").text.find("Academy-examination:") == -1

    with module.db() as connection:
        exam = connection.execute(
            "SELECT * FROM academy_examinations WHERE report_id=?", (report_id,)
        ).fetchone()
        assignment = connection.execute(
            "SELECT purpose FROM assignments WHERE id=?", (exam["assignment_id"],)
        ).fetchone()
        assert exam["status"] == "submitted"
        assert assignment["purpose"] == "academy"
        assert connection.execute("SELECT COUNT(*) AS c FROM academy_certificates").fetchone()["c"] == 0

    with TestClient(module.app, base_url="http://testserver") as admin:
        login(admin, "admin")
        queue = admin.get("/admin/academy/examinations")
        assert queue.status_code == 200
        assert "Demo Scout" in queue.text
        common = {
            "csrf": csrf_from(queue),
            "observation_score": "20",
            "context_score": "20",
            "conclusion_score": "10",
            "usability_score": "10",
            "ethics_score": "9",
            "feedback": "Tydlig återkoppling.",
        }
        too_low = admin.post(
            f"/admin/academy/examinations/{exam['id']}/review",
            data={**common, "decision": "pass"},
            follow_redirects=False,
        )
        assert too_low.status_code == 409

        changes = admin.post(
            f"/admin/academy/examinations/{exam['id']}/review",
            data={**common, "decision": "changes"},
            follow_redirects=False,
        )
        assert changes.status_code == 303

    with TestClient(module.app, base_url="http://testserver") as scout:
        login(scout, "scout")
        editor = scout.get(f"/reports/{report_id}/edit")
        assert editor.status_code == 200
        resubmit = scout.post(
            f"/reports/{report_id}/save",
            data={"csrf": csrf_from(editor), **valid_exam_data, "recommendation": "Kompletterad konkret rekommendation med tydlig matchplan.", "summary": "Kompletterad slutsats."},
            follow_redirects=False,
        )
        assert resubmit.status_code == 303

    with TestClient(module.app, base_url="http://testserver") as admin:
        login(admin, "admin")
        queue = admin.get("/admin/academy/examinations")
        approved = admin.post(
            f"/admin/academy/examinations/{exam['id']}/review",
            data={
                "csrf": csrf_from(queue),
                "decision": "pass",
                "observation_score": "20",
                "context_score": "20",
                "conclusion_score": "15",
                "usability_score": "10",
                "ethics_score": "5",
                "feedback": "Godkänd efter komplettering.",
            },
            follow_redirects=False,
        )
        assert approved.status_code == 303

    with module.db() as connection:
        certificate = connection.execute("SELECT * FROM academy_certificates").fetchone()
        enrollment = connection.execute(
            "SELECT status FROM academy_enrollments WHERE id=?", (exam["enrollment_id"],)
        ).fetchone()
        role = connection.execute("SELECT role FROM users WHERE id=?", (scout_id,)).fetchone()["role"]
        assert certificate is not None
        assert enrollment["status"] == "passed"
        assert role == "scout"

    with TestClient(module.app, base_url="http://testserver") as public:
        verification = public.get(f"/academy/certificates/{certificate['code']}")
        assert verification.status_code == 200
        assert "Demo Scout" in verification.text
        cert_pdf = public.get(f"/academy/certificates/{certificate['code']}/pdf")
        assert cert_pdf.status_code == 200
        assert cert_pdf.content.startswith(b"%PDF-")


def test_academy_admin_api_and_permissions(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with TestClient(module.app, base_url="http://testserver") as scout:
        login(scout, "scout")
        page = scout.get("/courses")
        assert scout.get("/admin/academy").status_code == 403
        assert scout.post(
            "/api/admin/academy/courses",
            headers={"X-CSRF-Token": csrf_from(page)},
            json={"title": "Otillåten kurs", "slug": "otillaten"},
        ).status_code == 403

    with TestClient(module.app, base_url="http://testserver") as admin:
        login(admin, "admin")
        page = admin.get("/admin/academy")
        response = admin.post(
            "/api/admin/academy/courses",
            headers={"X-CSRF-Token": csrf_from(page)},
            json={"title": "Nytt utkast", "slug": "nytt-utkast", "access_type": "paid", "price_ore": 99000},
        )
        assert response.status_code == 201
        assert response.json()["status"] == "draft"
        catalog = admin.get("/api/academy/courses")
        assert any(course["slug"] == "nytt-utkast" for course in catalog.json()["courses"])


def test_academy_resume_interest_and_accessibility(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        intro = connection.execute("SELECT id FROM academy_courses WHERE slug='introduktion-fotbollsscouting'").fetchone()
        advanced = connection.execute("SELECT id FROM academy_courses WHERE slug='spelaridentifiering-rekrytering'").fetchone()
        lessons = connection.execute(
            "SELECT l.id,q.correct_index FROM academy_lessons l JOIN academy_modules m ON m.id=l.module_id JOIN academy_lesson_questions q ON q.lesson_id=l.id WHERE m.course_id=? ORDER BY m.position,l.position",
            (intro["id"],),
        ).fetchall()

    with TestClient(module.app, base_url="http://testserver") as scout:
        login(scout, "scout")
        catalog = scout.get("/courses")
        assert 'class="skip-link"' not in catalog.text
        assert 'id="main-content"' in catalog.text
        assert 'aria-label="Huvudmeny"' in catalog.text
        scout.post(
            f"/courses/{intro['id']}/enroll",
            data={"csrf": csrf_from(catalog)},
            follow_redirects=False,
        )
        detail = scout.get("/courses/introduktion-fotbollsscouting")
        saved = scout.post(
            f"/api/academy/lessons/{lessons[0]['id']}/progress",
            headers={"X-CSRF-Token": csrf_from(detail)},
            json={"reflection": "Ett tillräckligt långt reflektionssvar.", "answer_index": lessons[0]["correct_index"]},
        )
        assert saved.json()["completed"] is True
        catalog = scout.get("/courses")
        assert f'/courses/lessons/{lessons[1]["id"]}' in catalog.text
        assert "Fortsätt där du slutade" in catalog.text
        assert 'role="progressbar"' in catalog.text

        advanced_page = scout.get("/courses/spelaridentifiering-rekrytering")
        interested = scout.post(
            f"/courses/{advanced['id']}/interest",
            data={"csrf": csrf_from(advanced_page)},
            follow_redirects=False,
        )
        assert interested.status_code == 303
        duplicate_page = scout.get(interested.headers["location"])
        assert "Du står på intresselistan" in duplicate_page.text
        duplicate = scout.post(
            f"/courses/{advanced['id']}/interest",
            data={"csrf": csrf_from(duplicate_page)},
            follow_redirects=False,
        )
        assert duplicate.status_code == 303

    with module.db() as connection:
        assert connection.execute("SELECT COUNT(*) AS c FROM academy_course_interest WHERE course_id=?",(advanced["id"],)).fetchone()["c"] == 1


def test_academy_publish_guard_and_lesson_versions(monkeypatch, tmp_path):
    module = load_application(monkeypatch, tmp_path)
    with module.db() as connection:
        advanced_id = connection.execute("SELECT id FROM academy_courses WHERE slug='spelaridentifiering-rekrytering'").fetchone()["id"]
        lesson = connection.execute("SELECT * FROM academy_lessons ORDER BY id LIMIT 1").fetchone()
        question = connection.execute("SELECT * FROM academy_lesson_questions WHERE lesson_id=?",(lesson["id"],)).fetchone()
        choices = json.loads(question["choices_json"])

    with TestClient(module.app, base_url="http://testserver") as admin:
        login(admin, "admin")
        admin_page = admin.get("/admin/academy")
        assert "Publiceringskontroll" in admin_page.text
        assert "punkter kvar" in admin_page.text
        blocked = admin.patch(
            f"/api/admin/academy/courses/{advanced_id}",
            headers={"X-CSRF-Token": csrf_from(admin_page)},
            json={"status": "published"},
        )
        assert blocked.status_code == 409

        editor = admin.get(f"/admin/academy/lessons/{lesson['id']}")
        first_title = lesson["title"] + " – redigerad"
        form = {
            "csrf": csrf_from(editor), "title": first_title,
            "learning_objective": lesson["learning_objective"], "body": lesson["body"],
            "example": lesson["example"], "exercise": lesson["exercise"], "video_url": lesson["video_url"],
            "diagram_kind": lesson["diagram_kind"], "status": lesson["status"],
            "question_text": question["question"], "choice_1": choices[0], "choice_2": choices[1], "choice_3": choices[2],
            "correct_index": str(question["correct_index"]), "explanation": question["explanation"],
        }
        assert admin.post(f"/admin/academy/lessons/{lesson['id']}",data=form,follow_redirects=False).status_code == 303
        editor = admin.get(f"/admin/academy/lessons/{lesson['id']}")
        assert "Version 1" in editor.text
        form["csrf"] = csrf_from(editor);form["title"] = lesson["title"] + " – andra versionen"
        assert admin.post(f"/admin/academy/lessons/{lesson['id']}",data=form,follow_redirects=False).status_code == 303

    with module.db() as connection:
        versions = connection.execute("SELECT * FROM academy_lesson_versions WHERE lesson_id=? ORDER BY version_number",(lesson["id"],)).fetchall()
        assert len(versions) == 2

    with TestClient(module.app, base_url="http://testserver") as admin:
        login(admin, "admin")
        editor = admin.get(f"/admin/academy/lessons/{lesson['id']}")
        restored = admin.post(
            f"/admin/academy/lessons/{lesson['id']}/versions/{versions[0]['id']}/restore",
            data={"csrf": csrf_from(editor)}, follow_redirects=False,
        )
        assert restored.status_code == 303

    with module.db() as connection:
        current = connection.execute("SELECT title FROM academy_lessons WHERE id=?",(lesson["id"],)).fetchone()
        assert current["title"] == first_title
        assert connection.execute("SELECT COUNT(*) AS c FROM academy_lesson_versions WHERE lesson_id=?",(lesson["id"],)).fetchone()["c"] == 3
        assert connection.execute("SELECT status FROM academy_courses WHERE id=?",(advanced_id,)).fetchone()["status"] == "draft"
