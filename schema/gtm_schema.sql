-- GTM tracker schema (Postgres / Supabase compatible; also runs on DuckDB for local testing)
-- Sources: Meta Ads (daily export), ClickUp (lead pipeline), Razorpay (payments), landing-page analytics.
-- One row = one fact. Dashboards read only from the views in sql/gtm_metrics.sql.

-- ---------- Marketing ----------
CREATE TABLE campaigns (
    campaign_id     VARCHAR PRIMARY KEY,          -- Meta campaign id
    campaign_name   VARCHAR NOT NULL,
    objective       VARCHAR NOT NULL CHECK (objective IN ('program', 'workshop')),
    start_date      DATE NOT NULL,
    end_date        DATE,
    status          VARCHAR NOT NULL DEFAULT 'active'   -- active / paused / ended
);

CREATE TABLE ad_sets (
    ad_set_id       VARCHAR PRIMARY KEY,
    campaign_id     VARCHAR NOT NULL REFERENCES campaigns(campaign_id),
    ad_set_name     VARCHAR NOT NULL,
    audience        VARCHAR                       -- e.g. 'Parents 35-50 Delhi NCR'
);

CREATE TABLE ads (
    ad_id           VARCHAR PRIMARY KEY,
    ad_set_id       VARCHAR NOT NULL REFERENCES ad_sets(ad_set_id),
    creative_name   VARCHAR NOT NULL,
    creative_format VARCHAR,                      -- reel / static / carousel
    landing_page_id VARCHAR
);

-- Daily pull from Meta Marketing API (n8n, 06:00 IST)
CREATE TABLE ad_daily_metrics (
    metric_date     DATE NOT NULL,
    ad_id           VARCHAR NOT NULL REFERENCES ads(ad_id),
    spend_inr       NUMERIC(12,2) NOT NULL,
    impressions     INTEGER NOT NULL,
    reach           INTEGER NOT NULL,
    link_clicks     INTEGER NOT NULL,
    leads           INTEGER NOT NULL,             -- Meta-reported form leads
    PRIMARY KEY (metric_date, ad_id)
);

CREATE TABLE landing_pages (
    landing_page_id VARCHAR PRIMARY KEY,
    page_url        VARCHAR NOT NULL,
    page_type       VARCHAR NOT NULL CHECK (page_type IN ('program', 'workshop'))
);

CREATE TABLE landing_page_daily (
    metric_date     DATE NOT NULL,
    landing_page_id VARCHAR NOT NULL REFERENCES landing_pages(landing_page_id),
    sessions        INTEGER NOT NULL,
    bounced         INTEGER NOT NULL,             -- left without scroll/click
    form_submits    INTEGER NOT NULL,
    avg_load_ms     INTEGER NOT NULL,
    PRIMARY KEY (metric_date, landing_page_id)
);

-- ---------- Funnel (mirrors ClickUp lead list) ----------
CREATE TABLE leads (
    lead_id         VARCHAR PRIMARY KEY,          -- ClickUp task id
    created_at      TIMESTAMP NOT NULL,
    source          VARCHAR NOT NULL CHECK (source IN ('meta_ads', 'organic', 'referral', 'workshop')),
    campaign_id     VARCHAR REFERENCES campaigns(campaign_id),
    ad_id           VARCHAR REFERENCES ads(ad_id),
    parent_name     VARCHAR,
    city            VARCHAR
);

-- Every ClickUp status change is written here by an n8n webhook. Append-only.
CREATE TABLE lead_stage_events (
    event_id        VARCHAR PRIMARY KEY,
    lead_id         VARCHAR NOT NULL REFERENCES leads(lead_id),
    stage           VARCHAR NOT NULL CHECK (stage IN (
                        'qualified',
                        'discovery_call_set',
                        'discovery_call_attended',
                        'ambition_interview_done',
                        'architect_session_done',
                        'converted',
                        'dropped')),
    occurred_at     TIMESTAMP NOT NULL,
    note            VARCHAR
);

-- ---------- Revenue ----------
CREATE TABLE enrolments (
    enrolment_id    VARCHAR PRIMARY KEY,
    lead_id         VARCHAR REFERENCES leads(lead_id),
    student_name    VARCHAR NOT NULL,
    plan_type       VARCHAR NOT NULL CHECK (plan_type IN ('trial_3m', 'full_program', 'renewal')),
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    fee_inr         NUMERIC(12,2) NOT NULL,
    renewed_from    VARCHAR                        -- enrolment_id of the trial it renewed
);

CREATE TABLE invoices (
    invoice_id      VARCHAR PRIMARY KEY,
    enrolment_id    VARCHAR NOT NULL REFERENCES enrolments(enrolment_id),
    issued_at       DATE NOT NULL,
    due_date        DATE NOT NULL,
    amount_inr      NUMERIC(12,2) NOT NULL,
    paid_at         DATE,                          -- NULL = unpaid
    razorpay_payment_id VARCHAR
);

CREATE TABLE workshops (
    workshop_id     VARCHAR PRIMARY KEY,
    workshop_date   DATE NOT NULL,                 -- fortnightly
    title           VARCHAR NOT NULL,
    seat_price_inr  NUMERIC(10,2) NOT NULL DEFAULT 3999,
    campaign_id     VARCHAR REFERENCES campaigns(campaign_id)
);

-- Razorpay payment.captured webhook -> n8n -> insert
CREATE TABLE workshop_bookings (
    booking_id      VARCHAR PRIMARY KEY,
    workshop_id     VARCHAR NOT NULL REFERENCES workshops(workshop_id),
    lead_id         VARCHAR REFERENCES leads(lead_id),
    paid_at         TIMESTAMP NOT NULL,
    amount_inr      NUMERIC(10,2) NOT NULL,
    razorpay_payment_id VARCHAR NOT NULL
);

-- Set by founders at the start of each month
CREATE TABLE monthly_targets (
    target_month        DATE PRIMARY KEY,          -- first day of month
    program_revenue_inr NUMERIC(12,2) NOT NULL,
    workshop_revenue_inr NUMERIC(12,2) NOT NULL,
    new_students        INTEGER NOT NULL
);
