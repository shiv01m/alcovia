"""
Dummy data for the student dashboard: 20 Alcovians, 1 Aug - 24 Oct 2026.
Writes data/students/*.csv and dashboards/students/data.js. Seeded.
"""
import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

random.seed(7)
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "students"
DASH = ROOT / "dashboards" / "students"
OUT.mkdir(parents=True, exist_ok=True)
DASH.mkdir(parents=True, exist_ok=True)

START, TODAY = date(2026, 8, 1), date(2026, 10, 24)
DAYS = [START + timedelta(d) for d in range((TODAY - START).days + 1)]

FIRST = ["Aarav", "Diya", "Kabir", "Myra", "Vihaan", "Anaya", "Reyansh", "Ira", "Arjun", "Saanvi",
         "Ishaan", "Kiara", "Advait", "Meher", "Dhruv", "Tara", "Rohan", "Zoya", "Neil", "Aditi"]
LAST = ["Mehta", "Kapoor", "Sethi", "Bansal", "Khanna", "Malhotra", "Arora", "Gupta", "Chawla", "Oberoi",
        "Jain", "Bhatia", "Suri", "Verma", "Nanda", "Gill", "Sood", "Ahuja", "Rao", "Dutta"]
ADVISORS = ["Riya (Advisor)", "Kunal (Advisor)", "Simran (Advisor)"]
SUBJECTS = [("Maths", True, 24), ("Science", True, 22), ("English", False, 14), ("Social Science", False, 20), ("Hindi", False, 15)]

students = []
for i in range(20):
    sid = f"S{i+1:02d}"
    students.append({
        "student_id": sid, "name": f"{FIRST[i]} {LAST[i]}", "grade": random.choice([8, 9, 9, 10, 10, 11]),
        "board": random.choice(["CBSE", "CBSE", "ICSE", "IB"]), "advisor": ADVISORS[i % 3],
        "plan_type": "trial_3m" if i % 3 == 0 else "full_program",
        "joined_on": START - timedelta(days=random.randint(0, 120)),
        "quarter_theme": random.choice(["social_work", "entrepreneurship"]),
        # hidden traits that drive the story
        "_drive": random.uniform(0.35, 0.95),          # engagement
        "_wear": i == 1,                                # brief: 1 student has connected WHOOP
        "_fade": random.random() < 0.3,                 # engagement fades after September
    })

# ---------- daily ----------
DORMANT = {"S03", "S06", "S08", "S11", "S14", "S17", "S20"}
daily = []
for s in students:
    for d in DAYS:
        drive = s["_drive"] * (0.65 if s["_fade"] and d >= date(2026, 9, 20) else 1.0)
        weekend = d.weekday() >= 5
        planned = random.random() < drive * (0.7 if weekend else 1.0)
        bp = random.randint(3, 6) if planned else 0
        bd = sum(random.random() < drive for _ in range(bp))
        quiz = random.random() < drive * 0.95
        score = round(min(100, max(10, random.gauss(45 + drive * 40, 12))), 1) if quiz else None
        focus = int(max(0, random.gauss(drive * 75, 25))) if random.random() < drive else 0
        active = sleep = rec = None
        if s["_wear"] and random.random() < 0.85:                   # sync gaps happen
            active = int(max(5, random.gauss(55 if not weekend else 80, 20)))
            sleep = round(min(10, max(4.5, random.gauss(7.1, 0.9))), 1)
            rec = int(min(99, max(15, random.gauss(62 - (7.5 - sleep) * 8, 12))))
        app = round(max(0.2, random.gauss(1.5 + drive * 2.0, 0.7)), 2)    # focus mode excluded
        if s["student_id"] in DORMANT and d > TODAY - timedelta(days=14):   # brief: 7 not opened in 2 weeks
            planned, bp, bd, quiz, score, focus, app = False, 0, 0, False, None, 0, 0.0
        daily.append({"metric_date": d, "student_id": s["student_id"], "timetable_planned": int(planned),
                      "blocks_planned": bp, "blocks_done": bd, "quiz_attempted": int(quiz),
                      "quiz_score_pct": score if score is not None else "", "focus_minutes": focus,
                      "active_minutes": active if active is not None else "",
                      "sleep_hours": sleep if sleep is not None else "", "recovery_pct": rec if rec is not None else "",
                      "app_minutes": app})

# ---------- subjects + chapters ----------
subjects, chapters, readiness_weekly = [], [], []
q_start, q_end = date(2026, 10, 1), date(2026, 12, 31)
for s in students:
    for name, tuition, n in SUBJECTS:
        subjects.append({"student_id": s["student_id"], "subject": name, "is_tuition": int(tuition),
                         "target_score": random.choice([75, 80, 85, 90]), "chapters_total": n})
        for c in range(1, n + 1):
            # chapters spread across the year: 25% per quarter (Apr-Mar academic year)
            q = min(3, (c - 1) * 4 // n)
            due = [date(2026, 6, 30), date(2026, 9, 30), date(2026, 12, 31), date(2027, 3, 31)][q]
            if due <= date(2026, 9, 30):
                stage = min(5, max(0, round(random.gauss(2.6 + s["_drive"] * 3.2, 1.1))))
            elif due <= q_end:
                stage = min(5, max(0, round(random.gauss(1.2 + s["_drive"] * 2.0, 1.0))))
            else:
                stage = 1 if random.random() < 0.15 else 0
            if s["_fade"] and due <= q_end:
                stage = max(0, stage - random.randint(0, 2))
            chapters.append({"student_id": s["student_id"], "subject": name, "chapter_no": c, "stage": stage,
                             "practice_acc": round(random.uniform(55, 92), 1) if stage >= 3 else "",
                             "paper_acc": round(random.uniform(65, 95), 1) if stage >= 4 else "",
                             "updated_at": TODAY - timedelta(days=random.randint(0, 40)), "due_by": due})
    # weekly readiness trend (share of chapters due so far that are exam-ready)
    for w in range(0, len(DAYS), 7):
        wk = DAYS[w]
        drift = (w / len(DAYS))
        base = s["_drive"] * (0.45 + 0.4 * drift) * (0.8 if s["_fade"] and wk >= date(2026, 9, 20) else 1.0)
        readiness_weekly.append({"week_start": wk, "student_id": s["student_id"],
                                 "readiness_pct": round(min(100, max(0, random.gauss(base * 100, 4))), 1)})

# ---------- tasks ----------
tasks, tn = [], 0
for s in students:
    for d in DAYS[::2]:
        for _ in range(random.randint(1, 2)):
            tn += 1
            due = d + timedelta(days=random.randint(1, 6))
            done = random.random() < (0.45 + s["_drive"] * 0.5) * (0.8 if s["_fade"] and d >= date(2026, 9, 20) else 1.0)
            comp = due + timedelta(days=random.choice([-2, -1, -1, 0, 0, 0, 0, 1, 3])) if done else None
            if comp and comp > TODAY:
                comp = None
            est = random.choice([0.5, 1, 1, 1.5, 2, 3])
            tasks.append({"task_id": f"T{tn:05d}", "student_id": s["student_id"],
                          "assigned_by": random.choice(["advisor", "advisor", "self"]),
                          "due_date": due, "completed_at": comp or "", "est_hours": est,
                          "actual_hours": round(est * random.uniform(0.7, 1.8), 1) if comp else ""})

# ---------- programme events ----------
events, en = [], 0
def add_events(etype, cadence, dates, invite, hold_p=0.93, score_fn=None):
    global en
    for d in dates:
        en += 1
        held = random.random() < hold_p
        for s in invite(d):
            att = held and random.random() < (0.55 + s["_drive"] * 0.45)
            rating = (min(5, max(1, round(random.gauss(3.4 + s["_drive"] * 1.4, 0.7))))) if att and random.random() < 0.8 else None
            score = round(score_fn(s), 1) if att and score_fn else None
            events.append({"event_id": f"EV{en:04d}", "student_id": s["student_id"], "event_type": etype, "cadence": cadence,
                           "planned_date": d, "held": int(held), "attended": int(att), "rating": rating or "",
                           "score": score if score is not None else ""})

weeks = [d for d in DAYS if d.weekday() == 1]                     # Tuesdays
months = [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)]
everyone = lambda d: students
for k in (0, 3):                                                   # 2 academic sessions a week
    for s in students:
        for w in weeks:
            en += 1
            d = w + timedelta(days=k)
            if d > TODAY:
                continue
            held = random.random() < 0.9
            att = held and random.random() < (0.6 + s["_drive"] * 0.4)
            events.append({"event_id": f"EV{en:04d}", "student_id": s["student_id"], "event_type": "academic_session",
                           "cadence": "week", "planned_date": d, "held": int(held), "attended": int(att),
                           "rating": (min(5, max(1, round(random.gauss(3.6 + s["_drive"], 0.7)))) if att and random.random() < 0.7 else ""),
                           "score": ""})
soft = lambda s: random.gauss(50 + s["_drive"] * 35, 9)          # avg of 11 soft skills, 0-100
add_events("workshop", "month", [m + timedelta(days=x) for m in months for x in (8, 22) if m + timedelta(days=x) <= TODAY], everyone, 0.97, soft)
pods = [students[i:i + 5] for i in range(0, 20, 5)]
for m in months:
    for p in pods:
        add_events("pod_session", "month", [m + timedelta(days=random.randint(10, 20))], lambda d, p=p: p, 0.85)
add_events("peer_session", "month", [m + timedelta(days=14) for m in months], lambda d: random.sample(students, 12), 0.8)
for s in students:
    for m in months:
        add_events("mentor_call", "month", [m + timedelta(days=random.randint(3, 26))], lambda d, s=s: [s], 0.82)
        add_events("branding_shoot", "month", [m + timedelta(days=random.randint(5, 25))], lambda d, s=s: [s], 0.7)
add_events("podcast", "quarter", [date(2026, 8, 29)], lambda d: random.sample(students, 6), 1.0, lambda s: random.gauss(70, 10))
add_events("competition", "quarter", [date(2026, 9, 12)], lambda d: random.sample(students, 8), 1.0, lambda s: random.gauss(60 + s["_drive"] * 25, 10))
add_events("parent_workshop", "quarter", [date(2026, 9, 26)], everyone, 1.0)
add_events("out_of_city", "quarter", [date(2026, 10, 17)], everyone, 1.0)
events = [e for e in events if e["planned_date"] <= TODAY]

# ---------- roadmaps ----------
milestones = []
for s in students:
    milestones.append({"student_id": s["student_id"], "roadmap": "career", "milestone_month": date(2026, 10, 1),
                       "title": "Career roadmap signed off", "done": int(random.random() < 0.6 + s["_drive"] * 0.3)})
    for m in months:
        for t in ("Monthly personal milestone", "Second personal milestone"):
            milestones.append({"student_id": s["student_id"], "roadmap": "personal", "milestone_month": m,
                               "title": t, "done": int(random.random() < s["_drive"])})
        milestones.append({"student_id": s["student_id"], "roadmap": "academic", "milestone_month": m,
                           "title": "Monthly score target met", "done": int(random.random() < s["_drive"] * 0.9)})


def write(name, rows):
    rows = [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows]
    with open(OUT / f"{name}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


for n, r in [("students", students), ("student_daily", daily), ("subjects", subjects), ("chapter_progress", chapters),
             ("tasks", tasks), ("program_events", events), ("roadmap_milestones", milestones),
             ("readiness_weekly", readiness_weekly)]:
    write(n, r)

# ---------- compact payload for the dashboard ----------
iso = lambda d: d.isoformat() if isinstance(d, date) else d
nz = lambda v: None if v == "" else v
payload = {
    "asOf": TODAY.isoformat(),
    "students": [[s["student_id"], s["name"], s["grade"], s["advisor"], s["plan_type"], int(s["_wear"])] for s in students],
    "daily": [[iso(r["metric_date"]), r["student_id"], r["timetable_planned"], r["blocks_planned"], r["blocks_done"],
               r["quiz_attempted"], nz(r["quiz_score_pct"]), r["focus_minutes"], nz(r["active_minutes"]),
               nz(r["sleep_hours"]), nz(r["recovery_pct"]), r["app_minutes"]] for r in daily],
    "subjects": [[r["student_id"], r["subject"], r["chapters_total"], r["target_score"]] for r in subjects],
    "chapters": [[r["student_id"], r["subject"], r["stage"], iso(r["due_by"])] for r in chapters],
    "readiness": [[iso(r["week_start"]), r["student_id"], r["readiness_pct"]] for r in readiness_weekly],
    "tasks": [[r["student_id"], iso(r["due_date"]), iso(r["completed_at"]) or None, r["est_hours"], nz(r["actual_hours"])] for r in tasks],
    "events": [[r["event_type"], r["cadence"], iso(r["planned_date"]), r["student_id"], r["held"], r["attended"],
                nz(r["rating"]), nz(r["score"])] for r in events],
    "milestones": [[r["student_id"], r["roadmap"], iso(r["milestone_month"]), r["done"]] for r in milestones],
}
js = "window.STUDENT_DATA = " + json.dumps(payload, separators=(",", ":")) + ";\n"
(DASH / "data.js").write_text(js)
print(f"students={len(students)} daily={len(daily)} chapters={len(chapters)} tasks={len(tasks)} "
      f"events={len(events)} milestones={len(milestones)} data.js={len(js)/1024:.0f}KB")
