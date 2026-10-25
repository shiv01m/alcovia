"""
Generates realistic dummy GTM data for Alcovia (1 May 2026 - 31 Oct 2026).
All numbers are invented for the assignment. Output: data/gtm/*.csv
Seeded, so every run gives the same data.
"""
import csv
import random
from datetime import date, datetime, timedelta
from pathlib import Path

random.seed(42)
OUT = Path(__file__).resolve().parent.parent / "data" / "gtm"
OUT.mkdir(parents=True, exist_ok=True)

START, END = date(2026, 5, 1), date(2026, 10, 31)
TODAY = date(2026, 10, 24)          # data is "live" up to this day
TRIAL_FEE, PROGRAM_FEE, SEAT = 45000, 180000, 3999


def days(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


def write(name, rows, cols):
    with open(OUT / f"{name}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


# ---------- campaigns, ad sets, ads, landing pages ----------
landing_pages = [
    {"landing_page_id": "LP1", "page_url": "alcovia.life/program", "page_type": "program"},
    {"landing_page_id": "LP2", "page_url": "alcovia.life/roadmap-call", "page_type": "program"},
    {"landing_page_id": "LP3", "page_url": "alcovia.life/workshop", "page_type": "workshop"},
    {"landing_page_id": "LP4", "page_url": "alcovia.life/career-day", "page_type": "workshop"},
]
lp_profile = {  # base bounce rate, base load ms
    "LP1": (0.42, 1900), "LP2": (0.55, 3400), "LP3": (0.38, 1600), "LP4": (0.61, 4100),
}

campaign_specs = [
    ("C01", "Program | Future-ready teen | Delhi NCR", "program", date(2026, 5, 1), date(2026, 8, 15)),
    ("C02", "Program | Parent testimonial reels", "program", date(2026, 6, 1), None),
    ("C03", "Program | Board exam anxiety", "program", date(2026, 7, 10), None),
    ("C04", "Program | Career clarity 13-17", "program", date(2026, 8, 20), None),
    ("C05", "Program | Retarget site visitors", "program", date(2026, 5, 15), None),
    ("C06", "Workshop | Career discovery Saturdays", "workshop", date(2026, 5, 1), None),
    ("C07", "Workshop | Meet a pilot / doctor / founder", "workshop", date(2026, 7, 1), None),
    ("C08", "Workshop | Summer special", "workshop", date(2026, 5, 10), date(2026, 7, 5)),
]
creative_pool = {
    "program": ["Parent reel: 'my son finally has a plan'", "Static: 3 roadmaps, 1 teen",
                "Carousel: day in an Alcovian's life", "Reel: advisor explains the 90-day trial",
                "Static: board exams are not the whole story", "Reel: podcast clip with founder guest"],
    "workshop": ["Reel: last workshop highlights", "Static: Rs 3,999 career day",
                 "Carousel: meet this Saturday's guest", "Reel: teens solving a pilot's crisis sim",
                 "Static: 30 seats only", "Reel: parent quote after workshop"],
}

campaigns, ad_sets, ads, ad_profile = [], [], [], {}
for cid, name, obj, s, e in campaign_specs:
    status = "ended" if e and e < TODAY else "active"
    campaigns.append({"campaign_id": cid, "campaign_name": name, "objective": obj,
                      "start_date": s, "end_date": e or "", "status": status})
    for k, aud in enumerate(["Parents 35-50 Delhi NCR", "Parents 35-50 Tier-1 metros"]):
        asid = f"{cid}-AS{k+1}"
        ad_sets.append({"ad_set_id": asid, "campaign_id": cid, "ad_set_name": f"{name} | {aud}",
                        "audience": aud})
        for j in range(3):
            aid = f"{asid}-AD{j+1}"
            creative = random.choice(creative_pool[obj])
            fmt = "reel" if creative.startswith("Reel") or creative.startswith("Parent reel") else (
                "carousel" if creative.startswith("Carousel") else "static")
            lp = random.choice(["LP1", "LP2"] if obj == "program" else ["LP3", "LP4"])
            ads.append({"ad_id": aid, "ad_set_id": asid, "creative_name": creative,
                        "creative_format": fmt, "landing_page_id": lp})
            base_ctr = random.uniform(0.006, 0.022) * (1.25 if fmt == "reel" else 1.0)
            ad_profile[aid] = {"campaign": cid, "obj": obj, "start": s, "end": min(e or TODAY, TODAY),
                               "ctr": base_ctr, "lp": lp,
                               "lead_rate": random.uniform(0.05, 0.14),
                               "daily_budget": random.uniform(120, 300),
                               "audience_size": random.randint(60000, 180000)}

# ---------- daily ad metrics ----------
ad_daily, lp_daily_acc = [], {}
for aid, p in ad_profile.items():
    cum_reach = 0
    for i, d in enumerate(days(p["start"], p["end"])):
        spend = round(p["daily_budget"] * random.uniform(0.8, 1.2), 2)
        impressions = int(spend / random.uniform(0.11, 0.17))       # CPM ~ Rs 110-170
        # reach shrinks as the audience saturates -> frequency climbs over the campaign's life
        fresh_share = max(0.18, 1 - cum_reach / p["audience_size"])
        reach = max(1, int(impressions * max(0.3, fresh_share) ** 0.75 * random.uniform(0.6, 0.8)))
        cum_reach += reach
        fatigue = max(0.45, 1 - i * 0.004)                          # CTR decays with age
        clicks = int(impressions * p["ctr"] * fatigue * random.uniform(0.8, 1.2))
        leads = sum(1 for _ in range(clicks) if random.random() < p["lead_rate"] * 0.12)
        ad_daily.append({"metric_date": d, "ad_id": aid, "spend_inr": spend,
                         "impressions": impressions, "reach": reach,
                         "link_clicks": clicks, "leads": leads})
        acc = lp_daily_acc.setdefault((d, p["lp"]), [0, 0])
        acc[0] += int(clicks * 0.88)        # sessions that actually loaded
        acc[1] += leads

lp_daily = []
for (d, lp), (sessions, submits) in sorted(lp_daily_acc.items()):
    organic = random.randint(5, 25)
    sessions += organic
    bounce_base, load_base = lp_profile[lp]
    drift = 1 + (0.25 if (lp == "LP2" and d >= date(2026, 9, 1)) else 0)   # LP2 got slower in Sep
    lp_daily.append({"metric_date": d, "landing_page_id": lp, "sessions": sessions,
                     "bounced": int(sessions * min(0.9, bounce_base * drift * random.uniform(0.9, 1.1))),
                     "form_submits": submits + random.randint(0, 2),
                     "avg_load_ms": int(load_base * drift * random.uniform(0.85, 1.15))})

# ---------- leads + stage events ----------
leads, events = [], []
lead_n = event_n = 0


def new_lead(created, source, cid="", aid=""):
    global lead_n
    lead_n += 1
    lid = f"L{lead_n:05d}"
    leads.append({"lead_id": lid, "created_at": created, "source": source, "campaign_id": cid,
                  "ad_id": aid, "parent_name": f"Parent {lead_n}",
                  "city": random.choice(["Gurugram", "Delhi", "Noida", "Faridabad", "Mumbai", "Bengaluru"])})
    return lid


def add_event(lid, stage, ts, note=""):
    global event_n
    event_n += 1
    events.append({"event_id": f"E{event_n:06d}", "lead_id": lid, "stage": stage,
                   "occurred_at": ts, "note": note})


# Program leads only enter the program funnel. Workshop-ad leads become bookings.
program_leads = []
for row in ad_daily:
    p = ad_profile[row["ad_id"]]
    for _ in range(row["leads"]):
        ts = datetime.combine(row["metric_date"], datetime.min.time()) + timedelta(minutes=random.randint(420, 1380))
        lid = new_lead(ts, "meta_ads" if p["obj"] == "program" else "workshop", p["campaign"], row["ad_id"])
        if p["obj"] == "program":
            program_leads.append((lid, ts, p["campaign"]))

for d in days(START, TODAY):                       # organic + referral trickle
    for src, rate in (("organic", 0.9), ("referral", 0.35)):
        if random.random() < rate:
            ts = datetime.combine(d, datetime.min.time()) + timedelta(minutes=random.randint(480, 1320))
            program_leads.append((new_lead(ts, src), ts, ""))

# campaign quality multiplier: some campaigns bring better-fit parents
quality = {"C01": 1.0, "C02": 1.35, "C03": 0.35, "C04": 1.15, "C05": 1.5, "": 1.6}
stage_flow = [  # (stage, base probability of reaching it from previous, days to reach)
    ("qualified", 0.42, (0, 2)),
    ("discovery_call_set", 0.62, (1, 4)),
    ("discovery_call_attended", 0.70, (2, 6)),
    ("ambition_interview_done", 0.74, (2, 7)),
    ("architect_session_done", 0.68, (3, 9)),
    ("converted", 0.24, (1, 6)),
]
converted = []
for lid, ts, cid in program_leads:
    q = quality.get(cid, 1.0) ** (1 / 3)           # spread the quality effect across the 6 stages
    t = ts
    for stage, prob, (lo, hi) in stage_flow:
        t = t + timedelta(days=random.randint(lo, hi), hours=random.randint(0, 8))
        if t.date() > TODAY:
            break                                   # still in progress
        if random.random() < min(0.95, prob * q):
            add_event(lid, stage, t)
            if stage == "converted":
                converted.append((lid, t.date()))
        else:
            add_event(lid, "dropped", t, note=f"dropped before {stage}")
            break

# ---------- enrolments, invoices, renewals ----------
enrolments, invoices = [], []
en_n = inv_n = 0


def add_invoice(eid, issued, amount, pay_prob=0.93):
    global inv_n
    inv_n += 1
    due = issued + timedelta(days=7)
    paid = None
    if random.random() < pay_prob:
        paid = issued + timedelta(days=random.randint(0, 12))
        if paid > TODAY:
            paid = None
    invoices.append({"invoice_id": f"INV{inv_n:05d}", "enrolment_id": eid, "issued_at": issued,
                     "due_date": due, "amount_inr": amount, "paid_at": paid or "",
                     "razorpay_payment_id": f"pay_{random.randint(10**9, 10**10)}" if paid else ""})


trials = []
for lid, d in converted:
    en_n += 1
    eid = f"EN{en_n:04d}"
    is_trial = random.random() < 0.62
    plan = "trial_3m" if is_trial else "full_program"
    fee = TRIAL_FEE if is_trial else PROGRAM_FEE
    end = d + timedelta(days=90 if is_trial else 365)
    enrolments.append({"enrolment_id": eid, "lead_id": lid, "student_name": f"Student {en_n}",
                       "plan_type": plan, "start_date": d, "end_date": end, "fee_inr": fee,
                       "renewed_from": ""})
    if is_trial:
        add_invoice(eid, d, fee)
        trials.append((eid, end))
    else:                                           # full program billed in 2 instalments
        add_invoice(eid, d, fee / 2)
        if d + timedelta(days=90) <= TODAY:
            add_invoice(eid, d + timedelta(days=90), fee / 2, pay_prob=0.85)

for eid, end in trials:                             # trials that came up for renewal
    if end <= TODAY and random.random() < 0.58:
        en_n += 1
        rid = f"EN{en_n:04d}"
        enrolments.append({"enrolment_id": rid, "lead_id": "", "student_name": f"Renewal of {eid}",
                           "plan_type": "renewal", "start_date": end, "end_date": end + timedelta(days=365),
                           "fee_inr": PROGRAM_FEE - TRIAL_FEE, "renewed_from": eid})
        add_invoice(rid, end, PROGRAM_FEE - TRIAL_FEE, pay_prob=0.8)

# ---------- workshops (fortnightly Saturdays) + bookings ----------
workshops, bookings = [], []
titles = ["A day as a pilot", "Inside a startup", "Doctor's emergency room sim", "Brand manager crisis",
          "Journalist on deadline", "Architect's city challenge", "Lawyer's courtroom sim",
          "Game designer sprint", "Chef's kitchen rush", "Diplomat's negotiation", "Data detective",
          "Film director's set", "Climate scientist mission"]
d, k, bk = date(2026, 5, 2), 0, 0
workshop_leads = [l for l in leads if l["source"] == "workshop"]
random.shuffle(workshop_leads)
while d <= END:
    k += 1
    wid = f"W{k:02d}"
    cid = "C08" if d < date(2026, 7, 5) and k % 2 == 0 else ("C07" if d >= date(2026, 7, 1) and k % 2 else "C06")
    workshops.append({"workshop_id": wid, "workshop_date": d, "title": titles[(k - 1) % len(titles)],
                      "seat_price_inr": SEAT, "campaign_id": cid})
    if d <= TODAY + timedelta(days=14):
        seats = random.randint(14, 34) if d <= TODAY else random.randint(5, 14)   # upcoming = partial
        for _ in range(seats):
            bk += 1
            lid = workshop_leads.pop()["lead_id"] if workshop_leads else ""
            paid = datetime.combine(d, datetime.min.time()) - timedelta(days=random.randint(1, 12), hours=random.randint(0, 20))
            if paid.date() > TODAY:
                continue
            bookings.append({"booking_id": f"B{bk:05d}", "workshop_id": wid, "lead_id": lid,
                             "paid_at": paid, "amount_inr": SEAT,
                             "razorpay_payment_id": f"pay_{random.randint(10**9, 10**10)}"})
    d += timedelta(days=14)

# ---------- monthly targets ----------
targets = []
for m, (prog, ws, ns) in zip(range(5, 11), [(100000, 200000, 2), (200000, 200000, 3), (300000, 200000, 5),
                                              (350000, 200000, 6), (400000, 200000, 5), (850000, 200000, 6)]):
    targets.append({"target_month": date(2026, m, 1), "program_revenue_inr": prog,
                    "workshop_revenue_inr": ws, "new_students": ns})

# ---------- write ----------
write("campaigns", campaigns, ["campaign_id", "campaign_name", "objective", "start_date", "end_date", "status"])
write("ad_sets", ad_sets, ["ad_set_id", "campaign_id", "ad_set_name", "audience"])
write("ads", ads, ["ad_id", "ad_set_id", "creative_name", "creative_format", "landing_page_id"])
write("ad_daily_metrics", ad_daily, ["metric_date", "ad_id", "spend_inr", "impressions", "reach", "link_clicks", "leads"])
write("landing_pages", landing_pages, ["landing_page_id", "page_url", "page_type"])
write("landing_page_daily", lp_daily, ["metric_date", "landing_page_id", "sessions", "bounced", "form_submits", "avg_load_ms"])
write("leads", leads, ["lead_id", "created_at", "source", "campaign_id", "ad_id", "parent_name", "city"])
write("lead_stage_events", events, ["event_id", "lead_id", "stage", "occurred_at", "note"])
write("enrolments", enrolments, ["enrolment_id", "lead_id", "student_name", "plan_type", "start_date", "end_date", "fee_inr", "renewed_from"])
write("invoices", invoices, ["invoice_id", "enrolment_id", "issued_at", "due_date", "amount_inr", "paid_at", "razorpay_payment_id"])
write("workshops", workshops, ["workshop_id", "workshop_date", "title", "seat_price_inr", "campaign_id"])
write("workshop_bookings", bookings, ["booking_id", "workshop_id", "lead_id", "paid_at", "amount_inr", "razorpay_payment_id"])
write("monthly_targets", targets, ["target_month", "program_revenue_inr", "workshop_revenue_inr", "new_students"])

print(f"campaigns={len(campaigns)} ads={len(ads)} ad_days={len(ad_daily)} leads={len(leads)} "
      f"program_leads={len(program_leads)} events={len(events)} enrolments={len(enrolments)} "
      f"invoices={len(invoices)} workshops={len(workshops)} bookings={len(bookings)}")
