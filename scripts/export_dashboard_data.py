"""
Builds the GTM marts in DuckDB and writes the compact dataset the dashboard reads:
    dashboards/gtm/data.js   (window.GTM_DATA = {...})
In production the same marts are Postgres views and the page fetches them from an API.
    python scripts/export_dashboard_data.py
"""
import json
from datetime import date
from pathlib import Path

import duckdb

from run_gtm_metrics import build

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dashboards" / "gtm"
OUT.mkdir(parents=True, exist_ok=True)


def rows(con, sql):
    return [list(r) for r in con.sql(sql).fetchall()]


def iso(v):
    return v.isoformat() if isinstance(v, date) else v


con = duckdb.connect()
build(con)

data = {
    "asOf": "2026-10-24",
    "generated": "dummy data for the Alcovia assignment",
    "campaigns": {r[0]: {"name": r[1], "objective": r[2], "start": iso(r[3])}
                  for r in rows(con, "SELECT campaign_id, campaign_name, objective, start_date FROM campaigns")},
    "ads": {r[0]: {"campaign": r[1], "adSet": r[2], "creative": r[3], "format": r[4], "lp": r[5]}
            for r in rows(con, """SELECT a.ad_id, s.campaign_id, a.ad_set_id, a.creative_name, a.creative_format,
                                         a.landing_page_id FROM ads a JOIN ad_sets s USING (ad_set_id)""")},
    "landingPages": {r[0]: {"url": r[1], "type": r[2]}
                     for r in rows(con, "SELECT landing_page_id, page_url, page_type FROM landing_pages")},
    # [date, trial, full, renewal, workshop, seats, newTrial, newFull, renewals]
    "revenueDaily": [[iso(r[0])] + [float(x) for x in r[1:]] for r in rows(con, """
        SELECT metric_date, trial_rev, full_program_rev, renewal_rev, workshop_rev, seats_sold,
               new_trial_students, new_full_students, renewals
        FROM mart_revenue_daily ORDER BY 1""")],
    # [month, programTarget, workshopTarget, studentTarget]
    "targets": [[iso(r[0]), float(r[1]), float(r[2]), int(r[3])] for r in rows(con, "SELECT * FROM monthly_targets ORDER BY 1")],
    # [leadDate, source, campaign, ad, qualified, callSet, attended, interview, architect, converted, dropped, daysInFunnel]
    "leads": [[iso(r[0]), r[1], r[2] or "", r[3] or ""] + [int(x or 0) for x in r[4:]] for r in rows(con, """
        SELECT lead_date, source, campaign_id, ad_id, is_qualified, call_set, call_attended, interview_done,
               architect_done, converted, dropped, days_in_funnel
        FROM mart_lead_journey ORDER BY lead_date""")],
    # [date, ad, spend, impressions, reach, clicks, leads]
    "adDaily": [[iso(r[0]), r[1], round(float(r[2])), int(r[3]), int(r[4]), int(r[5]), int(r[6])] for r in rows(con, """
        SELECT metric_date, ad_id, spend_inr, impressions, reach, link_clicks, leads
        FROM ad_daily_metrics ORDER BY 1""")],
    # [date, lp, sessions, bounced, formSubmits, avgLoadMs]
    "lpDaily": [[iso(r[0])] + list(r[1:]) for r in rows(con, """
        SELECT metric_date, landing_page_id, sessions, bounced, form_submits, avg_load_ms
        FROM landing_page_daily ORDER BY 1""")],
    # [workshopDate, title, seatsSold, revenue]
    "workshops": [[iso(r[0]), r[1], int(r[2]), float(r[3])] for r in rows(con, """
        SELECT w.workshop_date, w.title, COUNT(b.booking_id), COALESCE(SUM(b.amount_inr), 0)
        FROM workshops w LEFT JOIN workshop_bookings b USING (workshop_id)
        GROUP BY 1, 2 ORDER BY 1""")],
    # [invoice, student, plan, issued, due, amount]
    "unpaidInvoices": [[r[0], r[1], r[2], iso(r[3]), iso(r[4]), float(r[5])] for r in rows(con, """
        SELECT i.invoice_id, e.student_name, e.plan_type, i.issued_at, i.due_date, i.amount_inr
        FROM invoices i JOIN enrolments e USING (enrolment_id) WHERE i.paid_at IS NULL ORDER BY i.due_date""")],
    # [enrolment, student, trialEnds, renewed(0/1)]
    "trials": [[r[0], r[1], iso(r[2]), int(r[3])] for r in rows(con, """
        SELECT t.enrolment_id, t.student_name, t.end_date,
               CASE WHEN EXISTS (SELECT 1 FROM enrolments r WHERE r.renewed_from = t.enrolment_id) THEN 1 ELSE 0 END
        FROM enrolments t WHERE t.plan_type = 'trial_3m' ORDER BY t.end_date""")],
}

payload = "window.GTM_DATA = " + json.dumps(data, separators=(",", ":")) + ";\n"
(OUT / "data.js").write_text(payload)
print(f"wrote {OUT / 'data.js'} ({len(payload) / 1024:.0f} KB)")

# GitHub Pages needs a full HTML document; the source page is body-only.
src = (OUT / "index.src.html").read_text()
(OUT / "index.html").write_text(
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
    + src.replace("<style>", "<style>\nbody{margin:0}", 1).replace("\n<div class=\"wrap\">", "\n</head>\n<body>\n<div class=\"wrap\">", 1)
    + "\n</body>\n</html>\n")
print(f"wrote {OUT / 'index.html'}")
