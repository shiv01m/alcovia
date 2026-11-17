"""
Runs Q7 (weekly app adoption vs the 30-minute goal) from sql/student_metrics.sql
against the student CSVs on DuckDB, and prints the result.

    pip install duckdb
    python scripts/run_student_adoption.py
"""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
sql = (ROOT / "sql/student_metrics.sql").read_text()
q7 = sql[sql.index("-- Q7."):]

con = duckdb.connect()
con.execute(f"CREATE VIEW student_daily AS SELECT * FROM read_csv_auto('{ROOT / 'data/students/student_daily.csv'}')")
con.sql(q7).show()
