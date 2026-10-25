-- =====================================================================
-- Alcovia GTM tracker: metric layer
-- Postgres-compatible. Tested on DuckDB with the dummy data.
-- Pattern: daily-grain MARTS feed the dashboard (it filters by the date
-- picker); the numbered QUERIES answer each item in the brief directly.
-- Date range is set once in the params CTE of each query.
-- =====================================================================


-- ---------------------------------------------------------------------
-- MART 1: revenue by day (cash basis = when Razorpay captured payment)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW mart_revenue_daily AS
WITH program_cash AS (
    SELECT i.paid_at AS d,
           SUM(CASE WHEN e.plan_type = 'trial_3m'     THEN i.amount_inr ELSE 0 END) AS trial_rev,
           SUM(CASE WHEN e.plan_type = 'full_program' THEN i.amount_inr ELSE 0 END) AS full_program_rev,
           SUM(CASE WHEN e.plan_type = 'renewal'      THEN i.amount_inr ELSE 0 END) AS renewal_rev
    FROM invoices i
    JOIN enrolments e USING (enrolment_id)
    WHERE i.paid_at IS NOT NULL
    GROUP BY 1
),
workshop_cash AS (
    SELECT CAST(paid_at AS DATE) AS d, SUM(amount_inr) AS workshop_rev, COUNT(*) AS seats_sold
    FROM workshop_bookings
    GROUP BY 1
),
onboarded AS (
    SELECT start_date AS d,
           COUNT(*) FILTER (WHERE plan_type = 'trial_3m')     AS new_trial_students,
           COUNT(*) FILTER (WHERE plan_type = 'full_program') AS new_full_students,
           COUNT(*) FILTER (WHERE plan_type = 'renewal')      AS renewals
    FROM enrolments
    GROUP BY 1
),
calendar AS (
    SELECT d FROM program_cash UNION SELECT d FROM workshop_cash UNION SELECT d FROM onboarded
)
SELECT c.d                                   AS metric_date,
       COALESCE(p.trial_rev, 0)              AS trial_rev,
       COALESCE(p.full_program_rev, 0)       AS full_program_rev,
       COALESCE(p.renewal_rev, 0)            AS renewal_rev,
       COALESCE(p.trial_rev, 0) + COALESCE(p.full_program_rev, 0) + COALESCE(p.renewal_rev, 0) AS program_rev,
       COALESCE(w.workshop_rev, 0)           AS workshop_rev,
       COALESCE(w.seats_sold, 0)             AS seats_sold,
       COALESCE(o.new_trial_students, 0)     AS new_trial_students,
       COALESCE(o.new_full_students, 0)      AS new_full_students,
       COALESCE(o.renewals, 0)               AS renewals
FROM calendar c
LEFT JOIN program_cash  p ON p.d = c.d
LEFT JOIN workshop_cash w ON w.d = c.d
LEFT JOIN onboarded     o ON o.d = c.d;


-- ---------------------------------------------------------------------
-- MART 2: one row per program lead with its furthest stage (cohort by lead date)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW mart_lead_journey AS
SELECT l.lead_id,
       CAST(l.created_at AS DATE)                                              AS lead_date,
       l.source,
       l.campaign_id,
       l.ad_id,
       MAX(CASE WHEN s.stage = 'qualified'               THEN 1 ELSE 0 END)  AS is_qualified,
       MAX(CASE WHEN s.stage = 'discovery_call_set'      THEN 1 ELSE 0 END)  AS call_set,
       MAX(CASE WHEN s.stage = 'discovery_call_attended' THEN 1 ELSE 0 END)  AS call_attended,
       MAX(CASE WHEN s.stage = 'ambition_interview_done' THEN 1 ELSE 0 END)  AS interview_done,
       MAX(CASE WHEN s.stage = 'architect_session_done'  THEN 1 ELSE 0 END)  AS architect_done,
       MAX(CASE WHEN s.stage = 'converted'               THEN 1 ELSE 0 END)  AS converted,
       MAX(CASE WHEN s.stage = 'dropped'                 THEN 1 ELSE 0 END)  AS dropped,
       -- days from lead creation to the lead's last event (sign-up or drop-off)
       CAST(DATE_DIFF('day', MIN(l.created_at), MAX(s.occurred_at)) AS INTEGER) AS days_in_funnel
FROM leads l
LEFT JOIN lead_stage_events s USING (lead_id)
WHERE l.source <> 'workshop'
GROUP BY 1, 2, 3, 4, 5;


-- ---------------------------------------------------------------------
-- MART 3: ad performance by day, with qualified leads attributed back to the ad
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW mart_ad_daily AS
WITH q AS (
    SELECT ad_id, lead_date AS metric_date, SUM(is_qualified) AS qualified_leads, SUM(converted) AS conversions
    FROM mart_lead_journey
    WHERE ad_id IS NOT NULL
    GROUP BY 1, 2
)
SELECT m.metric_date, c.campaign_id, c.campaign_name, c.objective,
       a.ad_set_id, a.ad_id, a.creative_name, a.creative_format, a.landing_page_id,
       m.spend_inr, m.impressions, m.reach, m.link_clicks, m.leads,
       COALESCE(q.qualified_leads, 0) AS qualified_leads,
       COALESCE(q.conversions, 0)     AS conversions
FROM ad_daily_metrics m
JOIN ads a       USING (ad_id)
JOIN ad_sets s   USING (ad_set_id)
JOIN campaigns c ON c.campaign_id = s.campaign_id
LEFT JOIN q      ON q.ad_id = m.ad_id AND q.metric_date = m.metric_date;


-- =====================================================================
-- QUERIES: one per item in the brief
-- =====================================================================

-- Q1. Revenue target vs achievement (month)
WITH params AS (SELECT DATE '2026-10-01' AS month_start)
SELECT t.target_month,
       t.program_revenue_inr + t.workshop_revenue_inr               AS target_revenue,
       SUM(r.program_rev + r.workshop_rev)                           AS achieved_revenue,
       ROUND(100.0 * SUM(r.program_rev + r.workshop_rev)
             / (t.program_revenue_inr + t.workshop_revenue_inr), 1) AS pct_achieved,
       t.new_students                                                AS target_students,
       SUM(r.new_trial_students + r.new_full_students)               AS students_onboarded
FROM monthly_targets t, params p
JOIN mart_revenue_daily r
  ON r.metric_date >= p.month_start AND r.metric_date < p.month_start + INTERVAL 1 MONTH
WHERE t.target_month = p.month_start
GROUP BY t.target_month, t.program_revenue_inr, t.workshop_revenue_inr, t.new_students;

-- Q2. 3-month trial vs full program: sign-ups and revenue
WITH params AS (SELECT DATE '2026-05-01' AS start_date, DATE '2026-10-31' AS end_date)
SELECT e.plan_type,
       COUNT(DISTINCT e.enrolment_id)                          AS sign_ups,
       SUM(CASE WHEN i.paid_at IS NOT NULL THEN i.amount_inr ELSE 0 END) AS revenue_collected
FROM enrolments e
JOIN invoices i USING (enrolment_id), params p
WHERE e.start_date BETWEEN p.start_date AND p.end_date
GROUP BY 1
ORDER BY 1;

-- Q3. Students onboarded per month
SELECT DATE_TRUNC('month', start_date) AS month,
       COUNT(*) FILTER (WHERE plan_type = 'trial_3m')     AS trial,
       COUNT(*) FILTER (WHERE plan_type = 'full_program') AS full_program,
       COUNT(*) FILTER (WHERE plan_type <> 'renewal')     AS total_new
FROM enrolments
GROUP BY 1
ORDER BY 1;

-- Q4. Workshop revenue per fortnightly workshop (Razorpay bookings)
SELECT w.workshop_date, w.title,
       COUNT(b.booking_id)            AS seats_sold,
       COALESCE(SUM(b.amount_inr), 0) AS revenue_inr
FROM workshops w
LEFT JOIN workshop_bookings b USING (workshop_id)
GROUP BY 1, 2
ORDER BY 1;

-- Q5. Program vs workshop revenue by month
SELECT DATE_TRUNC('month', metric_date) AS month,
       SUM(program_rev)  AS program_revenue,
       SUM(workshop_rev) AS workshop_revenue,
       ROUND(100.0 * SUM(workshop_rev) / NULLIF(SUM(program_rev + workshop_rev), 0), 1) AS workshop_share_pct
FROM mart_revenue_daily
GROUP BY 1
ORDER BY 1;

-- Q6. Invoices generated but not paid (with ageing)
WITH params AS (SELECT DATE '2026-10-24' AS as_of)
SELECT i.invoice_id, e.student_name, e.plan_type, i.issued_at, i.due_date, i.amount_inr,
       CAST(DATE_DIFF('day', i.due_date, p.as_of) AS INTEGER) AS days_overdue,
       CASE WHEN p.as_of <= i.due_date                      THEN 'not due'
            WHEN DATE_DIFF('day', i.due_date, p.as_of) <= 15 THEN '1-15 days'
            WHEN DATE_DIFF('day', i.due_date, p.as_of) <= 30 THEN '16-30 days'
            ELSE '30+ days' END                             AS ageing_bucket
FROM invoices i
JOIN enrolments e USING (enrolment_id), params p
WHERE i.paid_at IS NULL
ORDER BY days_overdue DESC;

-- Q7. Renewals coming up for 3-month trial teens (next 30 days, not yet renewed)
WITH params AS (SELECT DATE '2026-10-24' AS as_of)
SELECT t.enrolment_id, t.student_name, t.end_date AS trial_ends,
       CAST(DATE_DIFF('day', p.as_of, t.end_date) AS INTEGER) AS days_left
FROM enrolments t, params p
WHERE t.plan_type = 'trial_3m'
  AND t.end_date BETWEEN p.as_of AND p.as_of + INTERVAL 30 DAY
  AND NOT EXISTS (SELECT 1 FROM enrolments r WHERE r.renewed_from = t.enrolment_id)
ORDER BY t.end_date;

-- Q8. Funnel: stage counts, show-up rate and interview drop-off (lead cohort in range)
WITH params AS (SELECT DATE '2026-05-01' AS start_date, DATE '2026-10-31' AS end_date),
f AS (SELECT j.* FROM mart_lead_journey j, params p WHERE j.lead_date BETWEEN p.start_date AND p.end_date)
SELECT COUNT(*)                 AS total_leads,
       SUM(is_qualified)        AS qualified_leads,
       SUM(call_set)            AS discovery_calls_set,
       SUM(call_attended)       AS discovery_calls_attended,
       ROUND(100.0 * SUM(call_attended) / NULLIF(SUM(call_set), 0), 1)            AS show_up_rate_pct,
       SUM(interview_done)      AS ambition_interviews,
       ROUND(100.0 * (1 - SUM(interview_done) * 1.0 / NULLIF(SUM(call_attended), 0)), 1) AS interview_drop_off_pct,
       SUM(architect_done)      AS architect_sessions,
       SUM(converted)           AS sign_ups
FROM f;

-- Q9. Top funnel metrics: cost per qualified lead, conversion %, organic leads, average journey
WITH params AS (SELECT DATE '2026-05-01' AS start_date, DATE '2026-10-31' AS end_date),
spend AS (
    SELECT SUM(spend_inr) AS program_spend
    FROM mart_ad_daily, params p
    WHERE objective = 'program' AND metric_date BETWEEN p.start_date AND p.end_date
),
f AS (SELECT j.* FROM mart_lead_journey j, params p WHERE j.lead_date BETWEEN p.start_date AND p.end_date)
SELECT ROUND(s.program_spend / NULLIF(SUM(f.is_qualified) FILTER (WHERE f.source = 'meta_ads'), 0)) AS cost_per_qualified_lead,
       ROUND(100.0 * SUM(f.converted) / COUNT(*), 2)                                                AS program_conversion_pct,
       COUNT(*) FILTER (WHERE f.source = 'organic')                                                 AS organic_leads,
       ROUND(AVG(f.days_in_funnel) FILTER (WHERE f.converted = 1), 1)                               AS avg_days_to_sign_up,
       ROUND(AVG(f.days_in_funnel) FILTER (WHERE f.dropped = 1), 1)                                 AS avg_days_to_drop_off
FROM f, spend s
GROUP BY s.program_spend;

-- Q10. Creatives: highest and lowest CTR (min 5,000 impressions so tiny ads don't skew it)
WITH params AS (SELECT DATE '2026-10-01' AS start_date, DATE '2026-10-31' AS end_date),
c AS (
    SELECT ad_id, creative_name, campaign_name, objective,
           SUM(impressions) AS impressions, SUM(link_clicks) AS clicks,
           ROUND(100.0 * SUM(link_clicks) / NULLIF(SUM(impressions), 0), 2) AS ctr_pct
    FROM mart_ad_daily, params p
    WHERE metric_date BETWEEN p.start_date AND p.end_date
    GROUP BY 1, 2, 3, 4
    HAVING SUM(impressions) >= 5000
)
SELECT *, CASE WHEN pr >= 0.8 THEN 'top 20%: scale'
               WHEN pr <= 0.2 THEN 'bottom 20%: refresh'
               ELSE '' END AS flag
FROM (SELECT c.*, PERCENT_RANK() OVER (PARTITION BY objective ORDER BY ctr_pct) AS pr FROM c) ranked
ORDER BY objective, ctr_pct DESC;

-- Q11. Ad-set frequency (impressions / reach); 3+ means the audience has seen it too often
WITH params AS (SELECT DATE '2026-10-18' AS start_date, DATE '2026-10-24' AS end_date)   -- last 7 days
SELECT ad_set_id, campaign_name,
       ROUND(SUM(impressions) * 1.0 / NULLIF(SUM(reach), 0), 2) AS frequency,
       CASE WHEN SUM(impressions) * 1.0 / NULLIF(SUM(reach), 0) >= 3 THEN 'CHANGE CREATIVE' ELSE 'ok' END AS action
FROM mart_ad_daily, params p
WHERE metric_date BETWEEN p.start_date AND p.end_date
GROUP BY 1, 2
ORDER BY frequency DESC;

-- Q12. Landing page health: drop-off (bounce) rate, load time, form conversion
WITH params AS (SELECT DATE '2026-10-01' AS start_date, DATE '2026-10-31' AS end_date)
SELECT lp.page_url, lp.page_type,
       SUM(d.sessions)                                                  AS sessions,
       ROUND(100.0 * SUM(d.bounced) / NULLIF(SUM(d.sessions), 0), 1)    AS drop_off_pct,
       ROUND(AVG(d.avg_load_ms) / 1000.0, 2)                            AS avg_load_sec,
       ROUND(100.0 * SUM(d.form_submits) / NULLIF(SUM(d.sessions), 0), 1) AS form_conversion_pct,
       CASE WHEN AVG(d.avg_load_ms) > 3000 OR SUM(d.bounced) * 1.0 / SUM(d.sessions) > 0.55
            THEN 'FIX' ELSE 'healthy' END                               AS status
FROM landing_page_daily d
JOIN landing_pages lp USING (landing_page_id), params p
WHERE d.metric_date BETWEEN p.start_date AND p.end_date
GROUP BY 1, 2
ORDER BY drop_off_pct DESC;

-- Q13. RCA: which campaigns to SCALE, REFRESH or DROP
-- Thresholds live in params so the team can tune them without touching logic.
WITH params AS (
    SELECT DATE '2026-09-25' AS start_date, DATE '2026-10-24' AS end_date,   -- last 30 days
           3.0  AS max_frequency,
           0.25 AS ctr_decay_trigger,     -- CTR down 25%+ vs campaign's first 14 days
           1.5  AS cpql_drop_multiple     -- CPQL 1.5x the median of active campaigns
),
recent AS (
    SELECT campaign_id, campaign_name, objective,
           SUM(spend_inr) AS spend, SUM(impressions) AS impressions, SUM(reach) AS reach,
           SUM(link_clicks) AS clicks, SUM(leads) AS leads,
           SUM(qualified_leads) AS qualified, SUM(conversions) AS conversions
    FROM mart_ad_daily, params p
    WHERE metric_date BETWEEN p.start_date AND p.end_date
    GROUP BY 1, 2, 3
),
launch AS (   -- CTR in each campaign's first 14 days = its baseline
    SELECT m.campaign_id, SUM(m.link_clicks) * 1.0 / NULLIF(SUM(m.impressions), 0) AS launch_ctr
    FROM mart_ad_daily m
    JOIN campaigns c USING (campaign_id)
    WHERE m.metric_date < c.start_date + INTERVAL 14 DAY
    GROUP BY 1
),
scored AS (
    SELECT r.*,
           r.spend / NULLIF(CASE WHEN r.objective = 'program' THEN r.qualified ELSE r.leads END, 0) AS cost_per_result,
           r.impressions * 1.0 / NULLIF(r.reach, 0)                  AS frequency,
           r.clicks * 1.0 / NULLIF(r.impressions, 0)                 AS ctr,
           1 - (r.clicks * 1.0 / NULLIF(r.impressions, 0)) / NULLIF(l.launch_ctr, 0) AS ctr_decay
    FROM recent r
    LEFT JOIN launch l USING (campaign_id)
),
bench AS (
    SELECT objective, MEDIAN(cost_per_result) AS median_cost FROM scored GROUP BY 1
)
SELECT s.campaign_name, s.objective,
       ROUND(s.spend) AS spend_30d,
       ROUND(s.cost_per_result) AS cost_per_result,      -- CPQL for program, cost per lead for workshop
       s.conversions,
       ROUND(s.frequency, 2) AS frequency,
       ROUND(100 * s.ctr, 2) AS ctr_pct,
       ROUND(100 * s.ctr_decay, 0) AS ctr_decay_pct,
       CASE
           WHEN s.cost_per_result > b.median_cost * p.cpql_drop_multiple                  THEN 'DROP'
           WHEN s.frequency >= p.max_frequency OR s.ctr_decay >= p.ctr_decay_trigger      THEN 'REFRESH'
           WHEN s.cost_per_result <= b.median_cost                                        THEN 'SCALE'
           ELSE 'HOLD'
       END AS verdict
FROM scored s
JOIN bench b USING (objective), params p
ORDER BY s.objective, s.cost_per_result;
