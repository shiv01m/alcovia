"""
Loads the dummy CSVs into a local DuckDB, builds the marts and runs every
metric query in sql/gtm_metrics.sql. Use it to check the SQL end to end.
    python scripts/run_gtm_metrics.py
"""
import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "gtm"
TABLES = ["campaigns", "ad_sets", "ads", "ad_daily_metrics", "landing_pages", "landing_page_daily",
          "leads", "lead_stage_events", "enrolments", "invoices", "workshops", "workshop_bookings",
          "monthly_targets"]


def statements(path):
    title = ""
    buf = []
    for line in (ROOT / path).read_text().splitlines():
        m = re.match(r"\s*--\s*(Q\d+\..*|MART \d+:.*)", line)
        if m:
            title = m.group(1)
        code = line.split("--")[0] if line.strip().startswith("--") else line
        buf.append(code)
        if code.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip().rstrip(";")
            buf = []
            if stmt:
                yield title, stmt


def build(con):
    for _, stmt in statements("schema/gtm_schema.sql"):
        con.execute(stmt)
    for t in TABLES:   # insert in FK order; empty strings become NULL
        con.execute(f"INSERT INTO {t} SELECT * FROM read_csv('{DATA / (t + '.csv')}', header=true, "
                    f"all_varchar=true, nullstr='')")
    for _, stmt in statements("sql/gtm_metrics.sql"):
        if "CREATE OR REPLACE VIEW" in stmt:
            con.execute(stmt)


if __name__ == "__main__":
    con = duckdb.connect()
    build(con)
    for title, stmt in statements("sql/gtm_metrics.sql"):
        if "CREATE OR REPLACE VIEW" in stmt:
            continue
        print(f"\n=== {title.strip()} ===")
        print(con.sql(stmt).limit(12))
