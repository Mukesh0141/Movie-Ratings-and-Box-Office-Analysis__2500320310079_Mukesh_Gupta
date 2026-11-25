"""P9 - Analysis and charts for Movie Ratings and Box-Office Analysis.

Run from the project folder:   python src/04_analysis_charts.py
Needs:  pip install pandas matplotlib

Reads   data/clean/movies_clean.csv, data/clean/movie_genres.csv
Writes  reports/kpis.json
        reports/charts/01_monthly_trend.png
        reports/charts/02_by_region.png
        reports/charts/03_by_category.png
        reports/charts/04_problem_area.png
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")                     # draw to files only, no window needed
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CLEAN = ROOT / "data" / "clean"
REPORTS = ROOT / "reports"
CHARTS = REPORTS / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------- settings and assumptions
# ASSUMPTION 1: money is in nominal US dollars (not adjusted for inflation), as in the source file.
# ASSUMPTION 2: rating averages use only reliable ratings (reliable_rating = True, i.e. 10+ votes).
# ASSUMPTION 3: revenue/profit/ROI averages use only movies that have the needed values;
#               budget = 0 and revenue = 0 were set to blank during cleaning, so they are excluded.
# ASSUMPTION 4: the dataset has NO region column, so original_language is used as the closest
#               stand-in for "region" (English, French, Hindi ...). It is language, not country.
# ASSUMPTION 5: a movie with several genres counts once in EACH genre, so genre bars overlap.
# ASSUMPTION 6: a "flop" means profit < 0 (revenue lower than budget); it ignores marketing cost.
MIN_MOVIES_REGION = 40      # a language needs 40+ movies with revenue to appear in the region chart
MIN_MOVIES_GENRE = 100      # a genre needs 100+ movies with profit for the problem-area chart
LANG_NAMES = {"en": "English", "fr": "French", "hi": "Hindi", "ru": "Russian", "es": "Spanish",
              "ja": "Japanese", "it": "Italian", "de": "German", "ko": "Korean", "zh": "Chinese",
              "cn": "Cantonese", "ta": "Tamil", "unknown": "Unknown"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
BLUE, ORANGE, RED, GREY = "#1F4E78", "#E07B39", "#C0392B", "#7F7F7F"

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlesize": 13})


def millions(x, _pos):
    return f"${x / 1e6:,.0f}M"


# ---------------------------------------------------------------- load
movies = pd.read_csv(CLEAN / "movies_clean.csv", parse_dates=["release_date"])
genres = pd.read_csv(CLEAN / "movie_genres.csv")
movies["release_month"] = movies["release_date"].dt.month
reliable = movies[movies["reliable_rating"]]
with_revenue = movies.dropna(subset=["revenue"])
with_profit = movies.dropna(subset=["profit"])
mg = genres.merge(movies, on="movie_id")           # one row per movie AND genre

# ---------------------------------------------------------------- KPIs
by_genre_rev = mg.dropna(subset=["revenue"]).groupby("genre")["revenue"].mean()
by_genre_rating = mg[mg["reliable_rating"]].groupby("genre")["rating"].agg(["mean", "count"])
by_genre_rating = by_genre_rating[by_genre_rating["count"] >= MIN_MOVIES_GENRE]
by_month = with_revenue.groupby("release_month")["revenue"].mean()
top_profit = with_profit.nlargest(1, "profit").iloc[0]

kpis = {
    "total_movies": int(len(movies)),
    "movies_with_revenue": int(len(with_revenue)),
    "movies_with_profit": int(len(with_profit)),
    "total_revenue_usd": float(with_revenue["revenue"].sum()),
    "avg_rating": round(float(reliable["rating"].mean()), 2),
    "avg_revenue_usd": round(float(with_revenue["revenue"].mean()), 0),
    "avg_profit_usd": round(float(with_profit["profit"].mean()), 0),
    "median_roi": round(float(with_profit["roi"].median()), 2),
    "pct_movies_profitable": round(float((with_profit["profit"] > 0).mean() * 100), 1),
    "pct_movies_flop": round(float((with_profit["profit"] < 0).mean() * 100), 1),
    # correlation uses Spearman (rank based) because revenue is very skewed
    "corr_rating_vs_revenue": round(float(reliable.dropna(subset=["revenue"])[["rating", "revenue"]]
                                          .corr(method="spearman").iloc[0, 1]), 3),
    "corr_budget_vs_revenue": round(float(with_profit[["budget", "revenue"]]
                                          .corr(method="spearman").iloc[0, 1]), 3),
    "top_genre_by_avg_revenue": str(by_genre_rev.idxmax()),
    "top_genre_by_avg_rating": str(by_genre_rating["mean"].idxmax()),
    "best_release_month_by_avg_revenue": MONTHS[int(by_month.idxmax()) - 1],
    "top_profit_movie": str(top_profit["title"]),
    "top_profit_usd": float(top_profit["profit"]),
}
with open(REPORTS / "kpis.json", "w", encoding="utf-8") as f:
    json.dump(kpis, f, indent=2)
print("Saved reports/kpis.json")
for k, v in kpis.items():
    print(f"  {k}: {v}")

# ---------------------------------------------------------------- chart 1: monthly trend
# ASSUMPTION 7: "monthly trend" = average revenue by calendar release month over ALL years combined
#               (a seasonality view), because one line per calendar date would be too crowded.
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(MONTHS, by_month.reindex(range(1, 13)).values, marker="o", color=BLUE, linewidth=2.5)
ax.set_title("Average Box-Office Revenue by Release Month")
ax.set_xlabel("Release month (all years combined)")
ax.set_ylabel("Average revenue per movie (USD millions)")
ax.yaxis.set_major_formatter(FuncFormatter(millions))
ax.grid(axis="y", alpha=0.3)
best = int(by_month.idxmax())
ax.annotate(f"Best month: {MONTHS[best - 1]}", (best - 1, by_month[best]),
            textcoords="offset points", xytext=(10, -5), color=ORANGE, fontweight="bold")
fig.tight_layout()
fig.savefig(CHARTS / "01_monthly_trend.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- chart 2: by region (language proxy)
reg = with_revenue.groupby("original_language").agg(movies=("movie_id", "count"),
                                                     avg_revenue=("revenue", "mean"))
reg = reg[reg["movies"] >= MIN_MOVIES_REGION].sort_values("avg_revenue")
labels = [f"{LANG_NAMES.get(c, c)} (n={int(n)})" for c, n in zip(reg.index, reg["movies"])]
fig, ax = plt.subplots(figsize=(9, 5))
ax.barh(labels, reg["avg_revenue"], color=BLUE)
ax.set_title("Average Revenue by Original Language (region proxy)")
ax.set_xlabel("Average revenue per movie (USD millions)")
ax.set_ylabel("Original language (n = movies with revenue)")
ax.xaxis.set_major_formatter(FuncFormatter(millions))
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
fig.savefig(CHARTS / "02_by_region.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- chart 3: by category (genre)
cat = by_genre_rev.sort_values()
cat = cat[cat.index != "Unknown"]
counts = mg.dropna(subset=["revenue"]).groupby("genre")["movie_id"].nunique()
cat = cat[counts.reindex(cat.index) >= 30]          # ignore genres with fewer than 30 movies
fig, ax = plt.subplots(figsize=(9, 7))
ax.barh(cat.index, cat.values, color=BLUE)
ax.set_title("Average Revenue by Genre")
ax.set_xlabel("Average revenue per movie (USD millions)")
ax.set_ylabel("Genre (a movie can appear in several genres)")
ax.xaxis.set_major_formatter(FuncFormatter(millions))
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
fig.savefig(CHARTS / "03_by_category.png", dpi=150)
plt.close(fig)

# ---------------------------------------------------------------- chart 4: problem area (flop rate by genre)
flop = (mg.dropna(subset=["profit"]).assign(flop=lambda d: d["profit"] < 0)
          .groupby("genre").agg(movies=("movie_id", "nunique"), flop_pct=("flop", "mean")))
flop = flop[flop["movies"] >= MIN_MOVIES_GENRE].sort_values("flop_pct")
flop["flop_pct"] *= 100
overall = kpis["pct_movies_flop"]
colors = [RED if v > overall else GREY for v in flop["flop_pct"]]
fig, ax = plt.subplots(figsize=(9, 6.5))
ax.barh(flop.index, flop["flop_pct"], color=colors)
ax.axvline(overall, color="black", linestyle="--", linewidth=1)
ax.text(overall + 0.3, -0.9, f"All movies: {overall:.1f}%", fontsize=9)
ax.set_title("Problem Area: Share of Movies That Lost Money, by Genre")
ax.set_xlabel("Movies with revenue below budget (%)")
ax.set_ylabel("Genre (red = worse than average)")
ax.grid(axis="x", alpha=0.3)
fig.tight_layout()
fig.savefig(CHARTS / "04_problem_area.png", dpi=150)
plt.close(fig)

print("Saved 4 charts in reports/charts")
