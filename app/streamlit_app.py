from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Movie Ratings & Box-Office Analysis",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 Movie Ratings and Box-Office Analysis")
st.write(
    "Explore how movie ratings, genres, release years, budgets, and "
    "box-office performance are related."
)

# ---------------------------------------------------------
# Locate project files
# ---------------------------------------------------------
# Expected project structure:
# project/
# ├── app/
# │   └── streamlit_app.py
# └── data/
#     └── clean/
#         ├── movies_clean.csv
#         └── movie_genres.csv

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent
DATA_DIR = PROJECT_DIR / "data" / "clean"

FACT_FILE = DATA_DIR / "movies_clean.csv"
GENRE_FILE = DATA_DIR / "movie_genres.csv"


@st.cache_data
def load_data(fact_path: str, genre_path: str):
    """Read the cleaned movie fact table and the movie-genre bridge table."""
    movies_df = pd.read_csv(fact_path)
    genres_df = pd.read_csv(genre_path) if Path(genre_path).exists() else pd.DataFrame()

    # Standardize key text fields.
    if "title" in movies_df.columns:
        movies_df["title"] = movies_df["title"].fillna("Untitled").astype(str)

    # Convert numeric columns safely.
    numeric_columns = [
        "release_year", "vote_average", "vote_count", "budget",
        "revenue", "profit_usd", "roi", "runtime"
    ]
    for column in numeric_columns:
        if column in movies_df.columns:
            movies_df[column] = pd.to_numeric(movies_df[column], errors="coerce")

    if not genres_df.empty:
        if "movie_id" not in genres_df.columns or "genre" not in genres_df.columns:
            raise ValueError(
                "movie_genres.csv must contain the columns 'movie_id' and 'genre'."
            )
        genres_df["movie_id"] = genres_df["movie_id"].astype(str)
        genres_df["genre"] = genres_df["genre"].fillna("Unknown").astype(str).str.strip()
        genres_df = genres_df.drop_duplicates(subset=["movie_id", "genre"])

    if "id" in movies_df.columns:
        movies_df["id"] = movies_df["id"].astype(str)

    return movies_df, genres_df


# ---------------------------------------------------------
# Check required files and load data
# ---------------------------------------------------------
if not FACT_FILE.exists():
    st.error(
        "The cleaned movie fact file was not found.\n\n"
        f"Expected location: `{FACT_FILE}`\n\n"
        "Run the data-cleaning notebook/script first and make sure "
        "`movies_clean.csv` is saved in `data/clean/`."
    )
    st.stop()

try:
    movies, movie_genres = load_data(str(FACT_FILE), str(GENRE_FILE))
except Exception as error:
    st.error(f"Could not load the cleaned data: {error}")
    st.stop()

required_columns = {"id", "title"}
missing_required = required_columns - set(movies.columns)
if missing_required:
    st.error(
        "The fact file is missing required columns: "
        + ", ".join(sorted(missing_required))
    )
    st.stop()

# Ensure the dashboard has a predictable numeric profit column.
if "profit_usd" not in movies.columns:
    if {"revenue", "budget"}.issubset(movies.columns):
        movies["profit_usd"] = movies["revenue"] - movies["budget"]
    else:
        movies["profit_usd"] = pd.NA

# ---------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------
st.sidebar.header("Filter movies")

filtered = movies.copy()

# Genre filter: use the bridge table because one movie can have
# more than one genre.
if not movie_genres.empty:
    genre_options = sorted(movie_genres["genre"].dropna().unique().tolist())
    selected_genres = st.sidebar.multiselect(
        "Genre",
        options=genre_options,
        default=[],
        help="Leave empty to include all genres.",
    )

    if selected_genres:
        selected_ids = movie_genres.loc[
            movie_genres["genre"].isin(selected_genres), "movie_id"
        ].unique()
        filtered = filtered[filtered["id"].isin(selected_ids)].copy()
else:
    st.sidebar.info(
        "Genre filter is unavailable because data/clean/movie_genres.csv "
        "was not found."
    )
    selected_genres = []

# Release-year filter.
if "release_year" in filtered.columns and filtered["release_year"].notna().any():
    year_values = filtered["release_year"].dropna()
    min_year = int(year_values.min())
    max_year = int(year_values.max())

    if min_year < max_year:
        selected_years = st.sidebar.slider(
            "Release year",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year),
        )
        filtered = filtered[
            filtered["release_year"].between(selected_years[0], selected_years[1])
        ].copy()
    else:
        st.sidebar.caption(f"Release year available: {min_year}")
else:
    st.sidebar.caption("Release-year filter unavailable.")

# Rating filter.
if "vote_average" in filtered.columns and filtered["vote_average"].notna().any():
    rating_values = filtered["vote_average"].dropna()
    rating_min = float(rating_values.min())
    rating_max = float(rating_values.max())

    if rating_min < rating_max:
        selected_rating = st.sidebar.slider(
            "Audience rating",
            min_value=0.0,
            max_value=10.0,
            value=(max(0.0, rating_min), min(10.0, rating_max)),
            step=0.1,
        )
        filtered = filtered[
            filtered["vote_average"].between(selected_rating[0], selected_rating[1])
            | filtered["vote_average"].isna()
        ].copy()
    else:
        st.sidebar.caption(f"Rating available: {rating_min:.1f}")
else:
    st.sidebar.caption("Rating filter unavailable.")

st.sidebar.markdown("---")
st.sidebar.caption("Clear a filter's selection or use its full range to see all records.")

# ---------------------------------------------------------
# KPI tiles
# ---------------------------------------------------------
movie_count = filtered["id"].nunique()

average_rating = (
    filtered["vote_average"].mean()
    if "vote_average" in filtered.columns else pd.NA
)
total_revenue = (
    filtered["revenue"].sum(min_count=1)
    if "revenue" in filtered.columns else pd.NA
)
total_profit = filtered["profit_usd"].sum(min_count=1)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

kpi1.metric("Movies", f"{movie_count:,.0f}")
kpi2.metric(
    "Average audience rating",
    f"{average_rating:.2f}/10" if pd.notna(average_rating) else "N/A",
)
kpi3.metric(
    "Total box-office revenue",
    f"${total_revenue:,.0f}" if pd.notna(total_revenue) else "N/A",
)
kpi4.metric(
    "Total profit",
    f"${total_profit:,.0f}" if pd.notna(total_profit) else "N/A",
)

st.caption(
    "Data source: The Movies Dataset – movies_metadata.csv "
    "(cleaned project data in data/clean/)."
)

st.markdown("---")

if filtered.empty:
    st.warning("No movies match the selected filters. Change or clear the sidebar filters.")
    st.stop()

# ---------------------------------------------------------
# Chart 1: Average revenue by genre
# ---------------------------------------------------------
st.subheader("1. Average Box-Office Revenue by Genre")

if not movie_genres.empty and "revenue" in filtered.columns:
    chart_genres = movie_genres[
        movie_genres["movie_id"].isin(filtered["id"])
    ].merge(
        filtered[["id", "revenue"]],
        left_on="movie_id",
        right_on="id",
        how="inner",
    )

    genre_revenue = (
        chart_genres.groupby("genre", as_index=False)
        .agg(
            average_revenue=("revenue", "mean"),
            movie_count=("movie_id", "nunique"),
        )
        .dropna(subset=["average_revenue"])
        .sort_values("average_revenue", ascending=False)
        .head(12)
    )

    if not genre_revenue.empty:
        fig_genre = px.bar(
            genre_revenue.sort_values("average_revenue"),
            x="average_revenue",
            y="genre",
            orientation="h",
            hover_data={"movie_count": True, "average_revenue": ":,.0f"},
            labels={
                "average_revenue": "Average revenue (USD)",
                "genre": "Genre",
                "movie_count": "Movies",
            },
            title="Top genres by average revenue",
        )
        st.plotly_chart(fig_genre, use_container_width=True)
        st.caption(
            "Genre groups overlap: a movie with multiple genres appears in each "
            "of its genre groups. Do not add genre-level counts or revenues together."
        )
    else:
        st.info("There are no valid revenue values for the selected movies.")
else:
    st.info("Genre chart requires movie_genres.csv and a revenue column.")

# ---------------------------------------------------------
# Chart 2: Average rating by release year
# ---------------------------------------------------------
st.subheader("2. Average Audience Rating by Release Year")

if {"release_year", "vote_average"}.issubset(filtered.columns):
    yearly_ratings = (
        filtered.dropna(subset=["release_year", "vote_average"])
        .groupby("release_year", as_index=False)
        .agg(
            average_rating=("vote_average", "mean"),
            movie_count=("id", "nunique"),
        )
        .sort_values("release_year")
    )

    if not yearly_ratings.empty:
        yearly_ratings["release_year"] = yearly_ratings["release_year"].astype(int)
        fig_year = px.line(
            yearly_ratings,
            x="release_year",
            y="average_rating",
            markers=True,
            hover_data={"movie_count": True, "average_rating": ":.2f"},
            labels={
                "release_year": "Release year",
                "average_rating": "Average rating",
                "movie_count": "Movies",
            },
            title="Average rating over time",
        )
        fig_year.update_yaxes(range=[0, 10])
        st.plotly_chart(fig_year, use_container_width=True)
    else:
        st.info("No rating and release-year values are available for this selection.")
else:
    st.info("Yearly rating chart requires release_year and vote_average columns.")

# ---------------------------------------------------------
# Chart 3: Top 10 movies by profit
# ---------------------------------------------------------
st.subheader("3. Top 10 Movies by Profit")

profit_data = filtered.dropna(subset=["profit_usd"]).copy()
if not profit_data.empty:
    top_movies = (
        profit_data.sort_values("profit_usd", ascending=False)
        .head(10)
        .sort_values("profit_usd", ascending=True)
    )

    fig_profit = px.bar(
        top_movies,
        x="profit_usd",
        y="title",
        orientation="h",
        hover_data={
            "budget": ":,.0f" if "budget" in top_movies.columns else False,
            "revenue": ":,.0f" if "revenue" in top_movies.columns else False,
            "profit_usd": ":,.0f",
        },
        labels={
            "profit_usd": "Profit (USD)",
            "title": "Movie",
        },
        title="Highest-profit movies in the filtered selection",
    )
    st.plotly_chart(fig_profit, use_container_width=True)
else:
    st.info(
        "Profit chart is unavailable because no selected movies have a valid "
        "profit value (both budget and revenue are needed)."
    )

# ---------------------------------------------------------
# Data table
# ---------------------------------------------------------
with st.expander("View filtered movie records"):
    display_columns = [
        column for column in [
            "id", "title", "release_year", "vote_average",
            "budget", "revenue", "profit_usd", "roi"
        ]
        if column in filtered.columns
    ]
    st.dataframe(
        filtered[display_columns].sort_values(
            "release_year", ascending=False, na_position="last"
        ),
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    f"Showing {len(filtered):,} filtered movie records. "
    "Financial KPIs and the profit chart use available financial values; "
    "missing budget/revenue records are not treated as zero."
)
