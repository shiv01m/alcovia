-- Student tracking schema (Postgres / Supabase). Feeds the student dashboard.
-- Rule: every row is written by the app, a form or an n8n flow. Advisors only enter
-- what a machine cannot know (session ratings, roadmap sign-off).

CREATE TABLE students (
    student_id      VARCHAR PRIMARY KEY,
    name            VARCHAR NOT NULL,
    grade           INTEGER NOT NULL,
    board           VARCHAR,                       -- CBSE / ICSE / IB
    advisor         VARCHAR NOT NULL,
    plan_type       VARCHAR NOT NULL,              -- trial_3m / full_program
    joined_on       DATE NOT NULL,
    quarter_theme   VARCHAR                        -- social_work / entrepreneurship / summer_program
);

-- ---------- Day level: one row per student per day, written by the app + n8n ----------
CREATE TABLE student_daily (
    metric_date         DATE NOT NULL,
    student_id          VARCHAR NOT NULL REFERENCES students(student_id),
    timetable_planned   BOOLEAN NOT NULL,          -- did the teen timebox the day in the app
    blocks_planned      INTEGER NOT NULL,          -- post-school time blocks planned
    blocks_done         INTEGER NOT NULL,          -- blocks marked done
    quiz_attempted      BOOLEAN NOT NULL,          -- 8 pm quiz (form -> n8n)
    quiz_score_pct      NUMERIC(5,2),
    focus_minutes       INTEGER NOT NULL,          -- app focus mode
    active_minutes      INTEGER,                   -- wearable (NULL = no wearable)
    sleep_hours         NUMERIC(4,2),              -- wearable
    recovery_pct        INTEGER,                   -- wearable
    app_minutes         NUMERIC(6,2) NOT NULL,     -- app sessions, focus mode excluded
    PRIMARY KEY (metric_date, student_id)
);

-- ---------- Week level: syllabus rigour ----------
CREATE TABLE subjects (
    student_id      VARCHAR NOT NULL REFERENCES students(student_id),
    subject         VARCHAR NOT NULL,
    is_tuition      BOOLEAN NOT NULL,              -- advisor is not the subject expert either way
    target_score    INTEGER NOT NULL,              -- for the next major exam
    chapters_total  INTEGER NOT NULL,
    PRIMARY KEY (student_id, subject)
);

-- Rigour stages per chapter. Readiness score = stages reached / 5.
-- 1 read  2 notes  3 practice >= 70%  4 past paper in time  5 exam-ready >= 80%
CREATE TABLE chapter_progress (
    student_id      VARCHAR NOT NULL,
    subject         VARCHAR NOT NULL,
    chapter_no      INTEGER NOT NULL,
    stage           INTEGER NOT NULL CHECK (stage BETWEEN 0 AND 5),
    practice_acc    NUMERIC(5,2),
    paper_acc       NUMERIC(5,2),
    updated_at      DATE NOT NULL,
    due_by          DATE NOT NULL,                 -- quarter plan: 25% of syllabus per quarter
    PRIMARY KEY (student_id, subject, chapter_no)
);

CREATE TABLE tasks (
    task_id         VARCHAR PRIMARY KEY,           -- ClickUp / app task id
    student_id      VARCHAR NOT NULL REFERENCES students(student_id),
    assigned_by     VARCHAR NOT NULL,              -- advisor / self
    due_date        DATE NOT NULL,
    completed_at    DATE,
    est_hours       NUMERIC(4,1),
    actual_hours    NUMERIC(4,1)
);

-- ---------- Week / month / quarter programme events ----------
-- One row per event per student invited. Quantity = held, Quality = attended + rating,
-- Performance = score (soft-skill average for workshops, readiness for competitions, etc.)
CREATE TABLE program_events (
    event_id        VARCHAR NOT NULL,
    student_id      VARCHAR NOT NULL REFERENCES students(student_id),
    event_type      VARCHAR NOT NULL CHECK (event_type IN (
                        'academic_session', 'workshop', 'pod_session', 'peer_session', 'mentor_call',
                        'branding_shoot', 'podcast', 'competition', 'parent_workshop', 'out_of_city')),
    cadence         VARCHAR NOT NULL,              -- week / month / quarter
    planned_date    DATE NOT NULL,
    held            BOOLEAN NOT NULL,
    attended        BOOLEAN NOT NULL,
    rating          INTEGER CHECK (rating BETWEEN 1 AND 5),   -- 1-tap rating in the app after the event
    score           NUMERIC(5,2),                  -- 0-100, see metric dictionary
    PRIMARY KEY (event_id, student_id)
);

-- ---------- Roadmaps ----------
CREATE TABLE roadmap_milestones (
    student_id      VARCHAR NOT NULL REFERENCES students(student_id),
    roadmap         VARCHAR NOT NULL CHECK (roadmap IN ('career', 'personal', 'academic')),
    milestone_month DATE NOT NULL,
    title           VARCHAR NOT NULL,
    done            BOOLEAN NOT NULL,
    PRIMARY KEY (student_id, roadmap, milestone_month, title)
);

-- Alerts sent by n8n (missed deadlines, syllabus deviation, low recovery streaks)
CREATE TABLE alerts (
    alert_id        VARCHAR PRIMARY KEY,
    student_id      VARCHAR NOT NULL REFERENCES students(student_id),
    rule            VARCHAR NOT NULL,
    raised_on       DATE NOT NULL,
    sent_to         VARCHAR NOT NULL,              -- advisor / parent / student
    resolved_on     DATE
);
