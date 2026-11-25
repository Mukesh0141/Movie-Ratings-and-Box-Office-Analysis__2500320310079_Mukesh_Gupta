"""P8 - Load the clean CSV files into a SQLite star schema and run the 7 queries.

Run from the project folder:   python src/03_load_sql.py
Needs only Python (no pandas):  csv + sqlite3 are built in.

Reads   data/clean/movies_clean.csv, data/clean/movie_genres.csv
        sql/schema.sql, sql/queries.sql
Writes  data/movies.db                    (SQLite database)
        reports/sql_results/q1.csv ... q7.csv
"""
import csv
import re
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
DB = ROOT / "data" / "movies.db"
RESULTS = ROOT / "reports" / "sql_results"
RESULTS.mkdir(parents=True, exist_ok=True)


def num(text, cast):
    """Empty text means missing (NULL) in the database."""
    return None if text == "" else cast(float(text)) if cast is int else cast(text)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- 1. create database from schema.sql
if DB.exists():
    DB.unlink()
con = sqlite3.connect(DB)
con.executescript((ROOT / "sql" / "schema.sql").read_text(encoding="utf-8"))
con.execute("PRAGMA foreign_keys = ON")

movies = read_csv(CLEAN / "movies_clean.csv")
links = read_csv(CLEAN / "movie_genres.csv")

# ---------------------------------------------------------------- 2. dimensions
con.executemany("INSERT INTO dim_movie VALUES (?, ?)",
                [(int(r["movie_id"]), r["title"]) for r in movies])

dates = sorted({r["release_date"] for r in movies if r["release_date"]})
date_rows = []
for s in dates:
    d = datetime.strptime(s[:10], "%Y-%m-%d")
    date_rows.append((int(d.strftime("%Y%m%d")), d.strftime("%Y-%m-%d"), d.year,
                      (d.month - 1) // 3 + 1, d.month, d.strftime("%B"), d.day))
con.executemany("INSERT INTO dim_date VALUES (?, ?, ?, ?, ?, ?, ?)", date_rows)

languages = sorted({r["original_language"] or "unknown" for r in movies})
lang_key = {name: i for i, name in enumerate(languages, 1)}
con.executemany("INSERT INTO dim_language VALUES (?, ?)", [(k, n) for n, k in lang_key.items()])

genres = sorted({r["genre"] for r in links})
genre_key = {name: i for i, name in enumerate(genres, 1)}
con.executemany("INSERT INTO dim_genre VALUES (?, ?)", [(k, n) for n, k in genre_key.items()])

# ---------------------------------------------------------------- 3. fact table (one row per movie)
fact = []
for r in movies:
    date_key = int(r["release_date"][:10].replace("-", "")) if r["release_date"] else 0
    fact.append((
        int(r["movie_id"]), date_key, lang_key[r["original_language"] or "unknown"],
        num(r["runtime"], int), num(r["budget"], int), num(r["revenue"], int),
        num(r["profit"], int), num(r["roi"], float), num(r["rating"], float),
        int(float(r["votes"])), 1 if r["reliable_rating"] == "True" else 0))
con.executemany("INSERT INTO fact_movie_performance VALUES (?,?,?,?,?,?,?,?,?,?,?)", fact)

# ---------------------------------------------------------------- 4. bridge table
con.executemany("INSERT INTO bridge_movie_genre VALUES (?, ?)",
                [(int(r["movie_id"]), genre_key[r["genre"]]) for r in links])
con.commit()

# ---------------------------------------------------------------- 5. checks
print("LOAD CHECKS")
checks = [("dim_movie", len(movies)), ("fact_movie_performance", len(movies)),
          ("bridge_movie_genre", len(links)), ("dim_genre", len(genres)),
          ("dim_language", len(languages)), ("dim_date", len(date_rows) + 1)]  # +1 = unknown date row
ok = True
for table, expected in checks:
    got = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    status = "PASS" if got == expected else "FAIL"
    ok &= got == expected
    print(f"  {status}  {table:<24} rows={got:>7}  expected={expected:>7}")
fk_errors = con.execute("PRAGMA foreign_key_check").fetchall()
print(f"  {'PASS' if not fk_errors else 'FAIL'}  foreign keys: {len(fk_errors)} violations")
assert ok and not fk_errors, "Load check failed - see FAIL lines above"

# ---------------------------------------------------------------- 6. run the 7 queries and save results
sql_text = (ROOT / "sql" / "queries.sql").read_text(encoding="utf-8")
parts = re.split(r"^-- (Q\d+) ", sql_text, flags=re.MULTILINE)   # [header, 'Q1', body, 'Q2', body ...]
print("\nQUERY RESULTS (saved in reports/sql_results)")
for tag, body in zip(parts[1::2], parts[2::2]):
    statement = body.split("\n", 1)[1]                         # drop the title line
    cur = con.execute(statement)
    header = [c[0] for c in cur.description]
    rows = cur.fetchall()
    with open(RESULTS / f"{tag.lower()}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {tag}: {len(rows)} rows -> {tag.lower()}.csv   first row: {rows[0]}")
con.close()
print("\nDatabase saved:", DB)