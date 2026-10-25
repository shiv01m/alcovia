# n8n workflows

Five workflows move data into one Postgres database, so neither dashboard depends on anyone updating a sheet. Each JSON file in this folder can be imported into n8n (Workflows → Import from file). They are designs: they need Alcovia's ClickUp, Razorpay, Meta, WhatsApp and database credentials before they can run.

## GTM 1 · ClickUp lead stages → database
`gtm_1_clickup_lead_stages.json`

```mermaid
flowchart LR
  A["ClickUp: lead status changed"] --> B["Map status to funnel stage"]
  B --> C["Insert into lead_stage_events"]
  C --> D{"Discovery call booked?"}
  D -- yes --> E["Smallest.ai: reminder calls 24 h and 1 h before"]
  D -- no --> F["Done"]
```

## GTM 2 · Razorpay payments → revenue tables
`gtm_2_razorpay_payments.json`

```mermaid
flowchart LR
  A["Razorpay webhook: payment captured"] --> B["Verify signature"]
  B --> C{"Workshop seat or invoice?"}
  C -- workshop --> D["Insert workshop booking"]
  C -- invoice --> E["Mark invoice paid"]
```

## GTM 3 · Daily Meta Ads pull (06:00 IST)
`gtm_3_meta_ads_daily.json`

```mermaid
flowchart LR
  A["Every day 06:00"] --> B["Meta Insights: yesterday, by ad"]
  B --> C["Shape rows"]
  C --> D["Upsert ad_daily_metrics"]
  D --> E{"Any ad set at frequency 3+?"}
  E -- yes --> F["ClickUp task: refresh creative"]
```

## Students 1 · 8 pm quiz scores
`students_1_quiz_scores.json`

```mermaid
flowchart LR
  A["Every day 20:45"] --> B["Read quiz form responses"]
  B --> C["Keep today's, score as %"]
  C --> D["Upsert into student_daily"]
```

## Students 2 · Nightly alerts
`students_2_nightly_alerts.json`

```mermaid
flowchart LR
  A["Every day 21:30"] --> B["Run alert rules: v_student_alerts_today"]
  B --> C{"Who gets it?"}
  C -- advisor --> D["ClickUp task for the advisor"]
  C -- parent --> E["WhatsApp message to the parent"]
  C -- student --> F["App notification to the student"]
  D --> G["Log in alerts table"]
  E --> G
  F --> G
```

Alert rules (in `sql/student_metrics.sql`): syllabus more than 25% behind plan, fewer than 60% of tasks on time, recovery under 40% for three days, five of the last seven quizzes skipped.

## Planned next · Sunday parent note

```mermaid
flowchart LR
  A["Every Sunday 10:00"] --> B["Pull each student's week: chapters moved, tasks done, focus minutes"]
  B --> C["Write 4 lines: finished, next, one win"]
  C --> D["WhatsApp to the parent"]
```
