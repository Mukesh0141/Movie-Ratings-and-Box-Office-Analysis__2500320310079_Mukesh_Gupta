import sqlite3
from pathlib import Path

import pandas as pd


# Project folders
PROJECT_ROOT = Path(__file__).resolve().parents[1]

MOVIES_CSV = PROJECT_ROOT / "data" / "clean" / "movies_clean.csv"
GENRES_CSV = PROJECT_ROOT / "data" / "clean" / "movie_genres.csv"
DB_PATH = PROJECT_ROOT / "data" / "movies.db"
REPORT_PATH = PROJECT_ROOT / "reports" / "test_results.csv"

results = []


def record_test(name, passed, details=""):
    """Print and store the result of one test."""
    status = "PASS" if passed else "FAIL"
    results.append({
        "test_case": name,
        "result": status,
        "details": str(details)
    })

    message = f"{status} {name}"
    if details:
        message += f" - {details}"
    print(message)


def get_table_columns(cursor, table_name):
    """Get the column names of a SQLite table."""
    cursor.execute(f'PRAGMA table_info("{table_name}")')
    return [row[1] for row in cursor.fetchall()]


def main():
    # Load the cleaned CSV files and existing SQLite database.
    try:
        movies = pd.read_csv(MOVIES_CSV)
        movie_genres = pd.read_csv(GENRES_CSV)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
    except Exception as exc:
        record_test(
            "test_00_load_files_and_database",
            False,
            str(exc)
        )
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(results).to_csv(REPORT_PATH, index=False)
        return

    # Test 1: Check duplicate movie IDs.
    duplicate_ids = int(movies["id"].duplicated().sum())

    record_test(
        "test_01_no_duplicate_movie_keys",
        duplicate_ids == 0,
        f"duplicate movie IDs: {duplicate_ids}"
    )

    # Test 2: Check duplicate movie/genre combinations.
    duplicate_pairs = int(
        movie_genres.duplicated(
            subset=["movie_id", "genre"]
        ).sum()
    )

    record_test(
        "test_02_no_duplicate_movie_genre_keys",
        duplicate_pairs == 0,
        f"duplicate movie-genre pairs: {duplicate_pairs}"
    )

    # Test 3: Check required fields in the movies CSV.
    required_columns = ["id", "title"]
    missing_columns = [
        column for column in required_columns
        if column not in movies.columns
    ]

    if missing_columns:
        record_test(
            "test_03_no_missing_required_fields",
            False,
            f"missing columns: {missing_columns}"
        )
    else:
        missing_rows = int(
            movies[required_columns].isna().any(axis=1).sum()
        )

        blank_titles = int(
            movies["title"].astype("string").str.strip().eq("").sum()
        )

        bad_rows = missing_rows + blank_titles

        record_test(
            "test_03_no_missing_required_fields",
            bad_rows == 0,
            f"missing/blank required values: {bad_rows}"
        )

    # Test 4: Check value ranges.
    # Missing values are allowed for optional movie fields.
    # Present values must be numeric and within the specified ranges.
    range_errors = []

    def check_range(column, minimum=None, maximum=None):
        if column not in movies.columns:
            range_errors.append(f"{column} column not found")
            return

        values = pd.to_numeric(movies[column], errors="coerce")

        # A non-empty value that cannot be converted to a number is invalid.
        invalid_format = movies[column].notna() & values.isna()

        # Check minimum and maximum only for values that are present.
        invalid_range = pd.Series(False, index=movies.index)

        if minimum is not None:
            invalid_range |= values.notna() & (values < minimum)

        if maximum is not None:
            invalid_range |= values.notna() & (values > maximum)

        invalid_count = int((invalid_format | invalid_range).sum())

        if invalid_count > 0:
            range_errors.append(
                f"{column}: {invalid_count} invalid row(s)"
            )

    check_range("vote_average", 0, 10)
    check_range("vote_count", 0, None)
    check_range("budget", 0, None)
    check_range("revenue", 0, None)
    check_range("runtime", 1, None)
    check_range("release_year", 1874, 2100)

    record_test(
        "test_04_valid_value_ranges",
        len(range_errors) == 0,
        "; ".join(range_errors)
        if range_errors
        else "all available values are within valid ranges"
    )

    # Test 5: Compare Python CSV revenue total with SQL fact-table total.
    try:
        python_total = (
            pd.to_numeric(movies["revenue"], errors="coerce")
            .fillna(0)
            .sum()
        )

        cursor.execute(
            """
            SELECT COALESCE(SUM(revenue_usd), 0)
            FROM fact_movie_performance
            """
        )

        sql_total = cursor.fetchone()[0] or 0

        totals_match = abs(
            float(python_total) - float(sql_total)
        ) < 0.01

        record_test(
            "test_05_python_revenue_total_equals_sql_revenue_total",
            totals_match,
            f"Python={python_total:.2f}; SQL={sql_total:.2f}"
        )

    except Exception as exc:
        record_test(
            "test_05_python_revenue_total_equals_sql_revenue_total",
            False,
            str(exc)
        )

    # Test 6: Every fact row must have a matching movie dimension row.
    try:
        dimension_columns = get_table_columns(
            cursor,
            "dim_movie"
        )

        if "movie_id" in dimension_columns:
            dimension_key = "movie_id"
        elif "id" in dimension_columns:
            dimension_key = "id"
        else:
            raise RuntimeError(
                "Could not identify the movie key in dim_movie. "
                f"Available columns: {dimension_columns}"
            )

        query = f"""
            SELECT COUNT(*)
            FROM fact_movie_performance AS f
            LEFT JOIN dim_movie AS d
                ON f.movie_id = d."{dimension_key}"
            WHERE d."{dimension_key}" IS NULL
        """

        cursor.execute(query)
        unmatched_rows = cursor.fetchone()[0]

        record_test(
            "test_06_every_fact_row_has_matching_movie_dimension",
            unmatched_rows == 0,
            f"unmatched fact rows: {unmatched_rows}"
        )

    except Exception as exc:
        record_test(
            "test_06_every_fact_row_has_matching_movie_dimension",
            False,
            str(exc)
        )

    conn.close()

    # Save all test results to reports/test_results.csv.
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(results).to_csv(
        REPORT_PATH,
        index=False
    )

    print(f"\nTest report saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
