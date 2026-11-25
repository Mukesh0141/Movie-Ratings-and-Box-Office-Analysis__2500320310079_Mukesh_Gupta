# Name : Mukesh Gupta
# Roll no : 2500320310079

"""P6 - Cleaning: movies_metadata.csv  ->  data/clean

Run from the project folder:   python src/01_Clean_Data.py

Reads   data/raw/movies_metadata.csv
Writes  data/clean/movies_clean.csv      one row per movie
        data/clean/movie_genres.csv      one row per movie AND genre
        data/clean/rejected_rows.csv     every removed row + the reason (nothing is silently dropped)
        reports/data_quality_log.csv     columns: issue, rule_applied, rows_affected
"""
import ast
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "movies_metadata.csv"
CLEAN = ROOT / "data" / "clean"
REPORTS = ROOT / "reports"
CLEAN.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

MIN_MONEY = 1_000   # a budget/revenue below this is a data-entry error
MIN_VOTES = 10      # a rating with fewer votes is not reliable

log = []
def record(issue, rule_applied, rows_affected):
    log.append({"issue": issue, "rule_applied": rule_applied, "rows_affected": int(rows_affected)})

rejected = []       # removed rows are collected here, never thrown away
def reject(frame, reason):
    out = frame.copy()
    out.insert(0, "reject_reason", reason)
    rejected.append(out)

# ------------------------------------------------------------------ load
df = pd.read_csv(RAW, low_memory=False, dtype=str, keep_default_na=True)
n_raw = len(df)
record("Raw rows loaded", "Read every row as text first so nothing is changed by pandas", n_raw)

# ------------------------------------------------------------------ 1. corrupt rows
bad_id = pd.to_numeric(df["id"], errors="coerce").isna()
record("Corrupt rows (id is not a number, columns shifted)",
       "Moved to rejected_rows.csv because the values cannot be trusted", bad_id.sum())
reject(df[bad_id], "corrupt row: id is not a number")
df = df[~bad_id].copy()
df["id"] = df["id"].astype(int)

# ------------------------------------------------------------------ 2. duplicates
dup = df.duplicated(subset="id", keep="first")
record("Duplicate movie id", "Kept the first row per id; the repeats moved to rejected_rows.csv", dup.sum())
reject(df[dup], "duplicate movie id")
df = df[~dup].copy()

# ------------------------------------------------------------------ 3. status
not_rel = df["status"].notna() & (df["status"] != "Released")
no_status = df["status"].isna()
record("Status is Rumored / Planned / In Production / Canceled",
       "Moved to rejected_rows.csv because an unreleased movie has no box office", not_rel.sum())
record("Status is missing", "Moved to rejected_rows.csv because release cannot be confirmed", no_status.sum())
reject(df[not_rel], "status is not Released")
reject(df[no_status], "status is missing")
df = df[~(not_rel | no_status)].copy()

# ------------------------------------------------------------------ 4. convert types
df["budget"] = pd.to_numeric(df["budget"], errors="coerce")
df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce")
df["runtime"] = pd.to_numeric(df["runtime"], errors="coerce")
df["vote_average"] = pd.to_numeric(df["vote_average"], errors="coerce")
df["vote_count"] = pd.to_numeric(df["vote_count"], errors="coerce")
df["release_date"] = pd.to_datetime(df["release_date"], errors="coerce")

# ------------------------------------------------------------------ 5. money columns (kept, value set to blank)
m = df["budget"] == 0
record("Budget = 0 (means unknown)", "Set budget to blank; the movie stays, but is left out of profit and ROI", m.sum())
df.loc[m, "budget"] = pd.NA
m = (df["budget"] > 0) & (df["budget"] < MIN_MONEY)
record(f"Budget between 1 and {MIN_MONEY - 1} (data-entry error)", "Set budget to blank", m.sum())
df.loc[m, "budget"] = pd.NA

m = df["revenue"] == 0
record("Revenue = 0 (means unknown)", "Set revenue to blank; the movie stays, but is left out of revenue averages", m.sum())
df.loc[m, "revenue"] = pd.NA
m = (df["revenue"] > 0) & (df["revenue"] < MIN_MONEY)
record(f"Revenue between 1 and {MIN_MONEY - 1} (data-entry error)", "Set revenue to blank", m.sum())
df.loc[m, "revenue"] = pd.NA

# ------------------------------------------------------------------ 6. runtime
m = df["runtime"] == 0
record("Runtime = 0 minutes (impossible)", "Set runtime to blank", m.sum())
df.loc[m, "runtime"] = pd.NA

# ------------------------------------------------------------------ 7. rating
m = (df["vote_average"] == 0) & (df["vote_count"] == 0)
record("Rating = 0 with 0 votes (means no rating)", "Set rating to blank", m.sum())
df.loc[m, "vote_average"] = pd.NA

low = df["vote_count"] < MIN_VOTES
record(f"Fewer than {MIN_VOTES} votes (rating not reliable)",
       "Kept the row; set reliable_rating = False so averages can skip it", low.sum())
df["reliable_rating"] = (~low) & df["vote_average"].notna()

# ------------------------------------------------------------------ 8. dates
m = df["release_date"].isna()
record("Release date missing", "Kept the row; release_year stays blank", m.sum())
df["release_year"] = df["release_date"].dt.year.astype("Int64")

# ------------------------------------------------------------------ 9. text
m = df["title"].isna()
record("Title missing", "Filled with 'Unknown title' so the row can still be counted", m.sum())
df.loc[m, "title"] = "Unknown title"

clean_title = df["title"].str.strip().str.replace(r"\s+", " ", regex=True)
m = clean_title != df["title"]
record("Title has extra or double spaces", "Trimmed and collapsed to single spaces", m.sum())
df["title"] = clean_title

m = df["original_language"].isna()
record("Language missing", "Filled with 'unknown'", m.sum())
df["original_language"] = df["original_language"].fillna("unknown").str.strip().str.lower()

# ------------------------------------------------------------------ 10. profit and ROI
df["profit"] = df["revenue"] - df["budget"]
df["roi"] = df["revenue"] / df["budget"]
n_profit = df["profit"].notna().sum()
record("Profit and ROI need both budget and revenue",
       "Calculated profit = revenue - budget and roi = revenue / budget only where both exist", n_profit)

# ------------------------------------------------------------------ 11. genres
def parse_genres(text):
    try:
        names = [g["name"].strip() for g in ast.literal_eval(text)]
    except (ValueError, SyntaxError, TypeError):
        names = []
    return names or ["Unknown"]

df["genre_list"] = df["genres"].map(parse_genres)
m = df["genre_list"].map(lambda g: g == ["Unknown"])
record("Genre list empty", "Genre set to 'Unknown'", m.sum())

m = df["genre_list"].map(len) >= 2
record("Movie has 2 or more genres (genres stored as text)",
       "Split into movie_genres.csv: one row per movie and genre. Genre totals overlap", m.sum())
movie_genres = (df[["id", "genre_list"]].explode("genre_list")
                  .rename(columns={"id": "movie_id", "genre_list": "genre"}))

# ------------------------------------------------------------------ 12. save
movies_clean = df[["id", "title", "release_date", "release_year", "original_language", "runtime",
                   "budget", "revenue", "profit", "roi", "vote_average", "vote_count",
                   "reliable_rating"]].rename(columns={"id": "movie_id", "vote_average": "rating",
                                                       "vote_count": "votes"})
movies_clean.to_csv(CLEAN / "movies_clean.csv", index=False)
movie_genres.to_csv(CLEAN / "movie_genres.csv", index=False)

rejected_df = pd.concat(rejected, ignore_index=True) if rejected else pd.DataFrame()
rejected_df.to_csv(CLEAN / "rejected_rows.csv", index=False)

# ------------------------------------------------------------------ 13. reconciliation: every raw row is accounted for
record("Rows written to movies_clean.csv", "Final clean rows", len(movies_clean))
record("Rows written to rejected_rows.csv", "Removed rows, each with its reason", len(rejected_df))
assert n_raw == len(movies_clean) + len(rejected_df), "Row count mismatch: some rows disappeared!"
record("Check: raw rows = clean rows + rejected rows", "Passed", n_raw)

pd.DataFrame(log, columns=["issue", "rule_applied", "rows_affected"]).to_csv(
    REPORTS / "data_quality_log.csv", index=False)

pd.set_option("display.width", 200, "display.max_colwidth", 90)
print(pd.DataFrame(log).to_string(index=False))
print("\nreject reasons:\n", rejected_df["reject_reason"].value_counts().to_string())