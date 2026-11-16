import json
from datetime import datetime

from academy_content import INTRO_COURSE, INTRO_QUIZ, DRAFT_COURSES


def init_academy(con):
    con.executescript('''
    CREATE TABLE IF NOT EXISTS academy_courses(
        id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '',
        level TEXT NOT NULL DEFAULT '', access_type TEXT NOT NULL CHECK(access_type IN ('free','paid')),
        price_ore INTEGER NOT NULL DEFAULT 0 CHECK(price_ore>=0), estimated_minutes INTEGER NOT NULL DEFAULT 0,
        study_time_label TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published','archived')),
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS academy_modules(
        id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES academy_courses(id) ON DELETE CASCADE,
        position INTEGER NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published')),
        UNIQUE(course_id,position)
    );
    CREATE TABLE IF NOT EXISTS academy_lessons(
        id INTEGER PRIMARY KEY, module_id INTEGER NOT NULL REFERENCES academy_modules(id) ON DELETE CASCADE,
        position INTEGER NOT NULL, slug TEXT NOT NULL UNIQUE, title TEXT NOT NULL, learning_objective TEXT NOT NULL DEFAULT '',
        body TEXT NOT NULL DEFAULT '', example TEXT NOT NULL DEFAULT '', exercise TEXT NOT NULL DEFAULT '',
        video_url TEXT NOT NULL DEFAULT '',
        diagram_kind TEXT NOT NULL DEFAULT 'none', status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published')),
        UNIQUE(module_id,position)
    );
    CREATE TABLE IF NOT EXISTS academy_lesson_questions(
        id INTEGER PRIMARY KEY, lesson_id INTEGER NOT NULL UNIQUE REFERENCES academy_lessons(id) ON DELETE CASCADE,
        question TEXT NOT NULL, choices_json TEXT NOT NULL, correct_index INTEGER NOT NULL, explanation TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS academy_quiz_questions(
        id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES academy_courses(id) ON DELETE CASCADE,
        position INTEGER NOT NULL, question TEXT NOT NULL, choices_json TEXT NOT NULL,
        correct_index INTEGER NOT NULL, explanation TEXT NOT NULL, UNIQUE(course_id,position)
    );
    CREATE TABLE IF NOT EXISTS academy_enrollments(
        id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES academy_courses(id),
        user_id INTEGER NOT NULL REFERENCES users(id),
        status TEXT NOT NULL DEFAULT 'in_progress' CHECK(status IN ('in_progress','quiz_passed','submitted','changes_requested','passed','failed')),
        enrolled_at TEXT NOT NULL, completed_at TEXT, UNIQUE(course_id,user_id)
    );
    CREATE TABLE IF NOT EXISTS academy_lesson_progress(
        id INTEGER PRIMARY KEY, enrollment_id INTEGER NOT NULL REFERENCES academy_enrollments(id) ON DELETE CASCADE,
        lesson_id INTEGER NOT NULL REFERENCES academy_lessons(id), reflection TEXT NOT NULL DEFAULT '',
        answer_index INTEGER, is_correct INTEGER NOT NULL DEFAULT 0, completed_at TEXT, updated_at TEXT NOT NULL,
        UNIQUE(enrollment_id,lesson_id)
    );
    CREATE TABLE IF NOT EXISTS academy_quiz_attempts(
        id INTEGER PRIMARY KEY, enrollment_id INTEGER NOT NULL REFERENCES academy_enrollments(id) ON DELETE CASCADE,
        score INTEGER NOT NULL, max_score INTEGER NOT NULL, passed INTEGER NOT NULL,
        answers_json TEXT NOT NULL, created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS academy_examinations(
        id INTEGER PRIMARY KEY, enrollment_id INTEGER NOT NULL REFERENCES academy_enrollments(id),
        assignment_id INTEGER REFERENCES assignments(id), report_id INTEGER REFERENCES reports(id),
        status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','submitted','changes_requested','passed','failed')),
        observation_score INTEGER, context_score INTEGER, conclusion_score INTEGER, usability_score INTEGER,
        ethics_score INTEGER, total_score INTEGER, critical_failure INTEGER NOT NULL DEFAULT 0,
        feedback TEXT NOT NULL DEFAULT '', submitted_at TEXT, reviewed_by INTEGER REFERENCES users(id), reviewed_at TEXT,
        created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS academy_certificates(
        id INTEGER PRIMARY KEY, enrollment_id INTEGER NOT NULL UNIQUE REFERENCES academy_enrollments(id),
        code TEXT NOT NULL UNIQUE, issued_at TEXT NOT NULL, issued_by INTEGER NOT NULL REFERENCES users(id), revoked_at TEXT
    );
    CREATE TABLE IF NOT EXISTS academy_course_interest(
        id INTEGER PRIMARY KEY, course_id INTEGER NOT NULL REFERENCES academy_courses(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at TEXT NOT NULL, notified_at TEXT, UNIQUE(course_id,user_id)
    );
    CREATE TABLE IF NOT EXISTS academy_lesson_versions(
        id INTEGER PRIMARY KEY, lesson_id INTEGER NOT NULL REFERENCES academy_lessons(id) ON DELETE CASCADE,
        version_number INTEGER NOT NULL, content_json TEXT NOT NULL,
        created_by INTEGER NOT NULL REFERENCES users(id), created_at TEXT NOT NULL,
        UNIQUE(lesson_id,version_number)
    );
    CREATE TABLE IF NOT EXISTS academy_audit_log(
        id INTEGER PRIMARY KEY, actor_user_id INTEGER REFERENCES users(id), action TEXT NOT NULL,
        entity_type TEXT NOT NULL, entity_id INTEGER, metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS academy_progress_enrollment_idx ON academy_lesson_progress(enrollment_id);
    CREATE INDEX IF NOT EXISTS academy_examinations_status_idx ON academy_examinations(status);
    CREATE INDEX IF NOT EXISTS academy_interest_course_idx ON academy_course_interest(course_id);
    CREATE INDEX IF NOT EXISTS academy_versions_lesson_idx ON academy_lesson_versions(lesson_id,version_number DESC);
    ''')
    lesson_columns={row['name'] for row in con.execute('PRAGMA table_info(academy_lessons)').fetchall()}
    if 'video_url' not in lesson_columns:
        con.execute("ALTER TABLE academy_lessons ADD COLUMN video_url TEXT NOT NULL DEFAULT ''")
    course_columns={row['name'] for row in con.execute('PRAGMA table_info(academy_courses)').fetchall()}
    if 'study_time_label' not in course_columns:
        con.execute("ALTER TABLE academy_courses ADD COLUMN study_time_label TEXT NOT NULL DEFAULT ''")
    _seed_courses(con)
    _migrate_legacy_progress(con)


def _insert_course(con, course):
    now=datetime.now().isoformat(timespec='minutes')
    con.execute('''INSERT OR IGNORE INTO academy_courses
        (slug,title,summary,level,access_type,price_ore,estimated_minutes,study_time_label,status,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)''',(
        course['slug'],course['title'],course['summary'],course['level'],course['access_type'],
        course['price_ore'],course['estimated_minutes'],course['study_time_label'],course['status'],now,now))
    con.execute("UPDATE academy_courses SET study_time_label=? WHERE slug=? AND study_time_label=''",(course['study_time_label'],course['slug']))
    return con.execute('SELECT id FROM academy_courses WHERE slug=?',(course['slug'],)).fetchone()['id']


def _seed_courses(con):
    course_id=_insert_course(con,INTRO_COURSE)
    for module_position,module in enumerate(INTRO_COURSE['modules'],start=1):
        con.execute('''INSERT OR IGNORE INTO academy_modules(course_id,position,title,summary,status)
            VALUES (?,?,?,?,?)''',(course_id,module_position,module['title'],module['summary'],'draft'))
        module_id=con.execute('SELECT id FROM academy_modules WHERE course_id=? AND position=?',(course_id,module_position)).fetchone()['id']
        for lesson_position,lesson in enumerate(module['lessons'],start=1):
            con.execute('''INSERT OR IGNORE INTO academy_lessons
                (module_id,position,slug,title,learning_objective,body,example,exercise,diagram_kind,status)
                VALUES (?,?,?,?,?,?,?,?,?,?)''',(
                module_id,lesson_position,lesson['slug'],lesson['title'],lesson['learning_objective'],
                lesson['body'],lesson['example'],lesson['exercise'],lesson['diagram_kind'],'draft'))
            lesson_id=con.execute('SELECT id FROM academy_lessons WHERE slug=?',(lesson['slug'],)).fetchone()['id']
            con.execute('''INSERT OR IGNORE INTO academy_lesson_questions
                (lesson_id,question,choices_json,correct_index,explanation) VALUES (?,?,?,?,?)''',(
                lesson_id,lesson['question'],json.dumps(lesson['choices'],ensure_ascii=False),
                lesson['correct_index'],lesson['explanation']))
    for position,(question,choices,correct,explanation) in enumerate(INTRO_QUIZ,start=1):
        con.execute('''INSERT OR IGNORE INTO academy_quiz_questions
            (course_id,position,question,choices_json,correct_index,explanation) VALUES (?,?,?,?,?,?)''',(
            course_id,position,question,json.dumps(choices,ensure_ascii=False),correct,explanation))
    for draft in DRAFT_COURSES:
        draft_id=_insert_course(con,draft)
        for position,module in enumerate(draft['modules'],start=1):
            title=module['title'];summary=module['summary']
            con.execute('''INSERT OR IGNORE INTO academy_modules(course_id,position,title,summary,status)
                VALUES (?,?,?,?,?)''',(draft_id,position,title,summary,'draft'))
            con.execute('''UPDATE academy_modules SET summary=? WHERE course_id=? AND position=?
                AND summary='Planerat originalinnehåll ska utvecklas och kvalitetssäkras före publicering.' ''',
                (summary,draft_id,position))


def _migrate_legacy_progress(con):
    course=con.execute("SELECT id FROM academy_courses WHERE slug='introduktion-fotbollsscouting'").fetchone()
    if not course:return
    legacy_users=con.execute('SELECT DISTINCT user_id FROM lessons UNION SELECT user_id FROM quiz_results').fetchall()
    for row in legacy_users:
        now=datetime.now().isoformat(timespec='minutes')
        con.execute('''INSERT OR IGNORE INTO academy_enrollments(course_id,user_id,status,enrolled_at)
            VALUES (?,?,?,?)''',(course['id'],row['user_id'],'in_progress',now))
        enrollment=con.execute('SELECT id FROM academy_enrollments WHERE course_id=? AND user_id=?',(course['id'],row['user_id'])).fetchone()
        for old in con.execute('SELECT lesson_index,done_at FROM lessons WHERE user_id=?',(row['user_id'],)).fetchall():
            lesson=con.execute('''SELECT l.id FROM academy_lessons l JOIN academy_modules m ON m.id=l.module_id
                WHERE m.course_id=? AND l.position=?''',(course['id'],old['lesson_index']+1)).fetchone()
            if lesson:
                con.execute('''INSERT OR IGNORE INTO academy_lesson_progress
                    (enrollment_id,lesson_id,reflection,answer_index,is_correct,completed_at,updated_at)
                    VALUES (?,?,?,NULL,0,?,?)''',(enrollment['id'],lesson['id'],'Migrerad från tidigare Academy-pilot.',old['done_at'],old['done_at']))


def academy_audit(con, actor_user_id, action, entity_type, entity_id=None, metadata=None):
    con.execute('''INSERT INTO academy_audit_log(actor_user_id,action,entity_type,entity_id,metadata_json,created_at)
        VALUES (?,?,?,?,?,?)''',(actor_user_id,action,entity_type,entity_id,json.dumps(metadata or {},ensure_ascii=False),datetime.now().isoformat(timespec='minutes')))
