-- =====================================================================
-- Student dashboard: metric layer (Postgres; tested on DuckDB)
-- Every KPI is read three ways: Quantity (did Alcovia deliver),
-- Quality (did the teen show up and value it), Performance (did the teen improve).
-- =====================================================================

-- Q1. Day-level habits per student for a date range
WITH params AS (SELECT DATE '2026-09-25' AS start_date, DATE '2026-10-24' AS end_date)
SELECT s.name,
       ROUND(100.0 * AVG(CASE WHEN d.timetable_planned THEN 1 ELSE 0 END), 0)        AS pct_days_planned,
       ROUND(100.0 * SUM(d.blocks_done) / NULLIF(SUM(d.blocks_planned), 0), 0)      AS block_adherence_pct,
       ROUND(100.0 * AVG(CASE WHEN d.quiz_attempted THEN 1 ELSE 0 END), 0)          AS quiz_participation_pct,
       ROUND(AVG(d.quiz_score_pct), 1)                                              AS avg_quiz_score,
       ROUND(AVG(d.focus_minutes), 0)                                               AS focus_min_per_day,
       ROUND(AVG(d.active_minutes), 0)                                              AS active_min_per_day,
       ROUND(AVG(d.sleep_hours), 1)                                                 AS sleep_h,
       ROUND(AVG(d.recovery_pct), 0)                                                AS recovery_pct,
       ROUND(AVG(d.app_minutes), 2)                                                 AS app_min_per_day   -- focus mode excluded; target 30
FROM student_daily d
JOIN students s USING (student_id), params p
WHERE d.metric_date BETWEEN p.start_date AND p.end_date
GROUP BY s.name
ORDER BY app_min_per_day;

-- Q2. Syllabus rigour: chapter readiness by student and subject
-- readiness = stages reached / 5 across chapters due; exam_ready = stage 5 (past paper >= 80%)
SELECT s.name, c.subject,
       COUNT(*) FILTER (WHERE c.due_by <= DATE '2026-09-30')                                        AS chapters_due,
       COUNT(*) FILTER (WHERE c.due_by <= DATE '2026-09-30' AND c.stage = 5)                        AS exam_ready,
       ROUND(100.0 * SUM(c.stage) FILTER (WHERE c.due_by <= DATE '2026-09-30')
             / NULLIF(5 * COUNT(*) FILTER (WHERE c.due_by <= DATE '2026-09-30'), 0), 0)             AS readiness_pct
FROM chapter_progress c
JOIN students s USING (student_id)
GROUP BY s.name, c.subject
ORDER BY readiness_pct;

-- Q3. Tasks: completion, deadline adherence, time-estimation accuracy
SELECT s.name,
       COUNT(*)                                                                         AS tasks,
       ROUND(100.0 * COUNT(t.completed_at) / COUNT(*), 0)                               AS completion_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE t.completed_at <= t.due_date) / COUNT(*), 0) AS on_time_pct,
       ROUND(100 * (1 - AVG(ABS(t.actual_hours - t.est_hours) / t.actual_hours)), 0)    AS estimate_accuracy_pct
FROM tasks t
JOIN students s USING (student_id)
WHERE t.due_date <= DATE '2026-10-24'
GROUP BY s.name
ORDER BY on_time_pct;

-- Q4. Programme events: quantity, quality, performance per event type
SELECT event_type, cadence,
       COUNT(DISTINCT event_id)                                                   AS planned,
       COUNT(DISTINCT event_id) FILTER (WHERE held)                               AS held,                -- Quantity
       ROUND(100.0 * COUNT(*) FILTER (WHERE held AND attended)
             / NULLIF(COUNT(*) FILTER (WHERE held), 0), 0)                        AS attendance_pct,      -- Quality
       ROUND(AVG(rating), 2)                                                      AS avg_rating,          -- Quality
       ROUND(AVG(score), 1)                                                       AS avg_score            -- Performance
FROM program_events
GROUP BY event_type, cadence
ORDER BY cadence, event_type;

-- Q5. Roadmaps
SELECT roadmap,
       COUNT(*)                                         AS milestones,
       ROUND(100.0 * AVG(CASE WHEN done THEN 1 ELSE 0 END), 0) AS done_pct
FROM roadmap_milestones
GROUP BY roadmap;

-- Q6. Alert rules (the nightly n8n workflow reads this view)
-- X% deviation, task and recovery thresholds are set by the academic team.
CREATE OR REPLACE VIEW v_student_alerts_today AS
WITH run_day AS (SELECT DATE '2026-10-24' AS d),
syl AS (
    SELECT student_id,
           1 - SUM(stage) * 1.0 / NULLIF(5 * COUNT(*), 0) AS behind
    FROM chapter_progress, run_day
    WHERE due_by <= DATE '2026-09-30'
    GROUP BY student_id
),
tsk AS (
    SELECT student_id, COUNT(*) FILTER (WHERE completed_at <= due_date) * 1.0 / COUNT(*) AS on_time
    FROM tasks, run_day
    WHERE due_date BETWEEN run_day.d - INTERVAL 30 DAY AND run_day.d
    GROUP BY student_id HAVING COUNT(*) >= 5
),
rec AS (
    SELECT student_id, AVG(recovery_pct) AS rec3
    FROM student_daily, run_day
    WHERE metric_date > run_day.d - INTERVAL 3 DAY AND recovery_pct IS NOT NULL
    GROUP BY student_id HAVING COUNT(*) = 3
),
quiz AS (
    SELECT student_id, COUNT(*) FILTER (WHERE NOT quiz_attempted) AS missed
    FROM student_daily, run_day
    WHERE metric_date > run_day.d - INTERVAL 7 DAY
    GROUP BY student_id
),
flags AS (
    SELECT student_id, 'syllabus_behind' AS rule_code, 'Syllabus behind plan' AS rule,
           CAST(ROUND(100 * behind) AS INTEGER) || '% behind the quarter plan' AS detail, 'advisor' AS sent_to
    FROM syl WHERE behind > 0.25
    UNION ALL
    SELECT student_id, 'syllabus_behind', 'Syllabus behind plan',
           CAST(ROUND(100 * behind) AS INTEGER) || '% behind the quarter plan', 'parent'
    FROM syl WHERE behind > 0.25
    UNION ALL
    SELECT student_id, 'deadlines', 'Missing deadlines', CAST(ROUND(100 * on_time) AS INTEGER) || '% of tasks on time', 'advisor'
    FROM tsk WHERE on_time < 0.60
    UNION ALL
    SELECT student_id, 'recovery', 'Low recovery', CAST(ROUND(rec3) AS INTEGER) || '% average over 3 days', 'advisor'
    FROM rec WHERE rec3 < 40
    UNION ALL
    SELECT student_id, 'quiz', 'Skipping the 8 pm quiz', missed || ' of last 7 missed', 'student'
    FROM quiz WHERE missed >= 5
)
SELECT f.*, s.name AS student_name, s.advisor
FROM flags f JOIN students s USING (student_id);

SELECT rule, sent_to, COUNT(*) AS students FROM v_student_alerts_today GROUP BY 1, 2 ORDER BY 1, 2;
