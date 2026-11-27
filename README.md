# Movie Ratings and Box-Office Analysis

## 1. Project Overview

**Movie Ratings and Box-Office Analysis** is a data analytics project that organizes and analyzes movie information, audience ratings, genres, and box-office performance.

The project uses Python and Pandas for working with data, SQLite and SQL for structured storage and queries, and Power BI for interactive reporting.

## 2. Problem Statement

Movie ratings and box-office information can be difficult to analyze together when the data is stored across multiple fields and files. This project cleans and organizes movie data, stores it in a relational database, and presents the results through interactive dashboards. It helps users explore movie ratings, compare genres, and examine financial performance.

## 3. Key Results

The following figures are from the current project data and checks:

| Metric | Result |
|---|---:|
| Movie records in `movies_clean.csv` | 44,985 |
| Records with a rating value | 42,145 |
| Records with budget information | 8,613 |
| Records with revenue information | 7,233 |
| Total revenue calculated in Python | $509,333,453,449 |
| Total revenue calculated in SQL | $509,333,453,449 |
| Tables in the SQLite database | 6 |

**Validation result:** The Python CSV revenue total matches the SQL fact-table revenue total.

The current pipeline test run also passed these checks:
- No duplicate movie IDs in the cleaned movie CSV.
- No duplicate movie/genre pairs in the genre bridge CSV.
- No missing or blank required movie ID/title values.
- Python and SQL revenue totals match.
- Every fact row has a matching movie dimension row.

The valid-value-range test is being refined to distinguish missing optional values from invalid values. Do not treat that test as passed until the latest test run confirms it.

## 4. Tools and Technologies

- **Python** — project scripting and data validation
- **Pandas** — reading and analyzing CSV data
- **SQLite** — relational database
- **SQL** — database queries and validation
- **Power BI Desktop** — interactive dashboard and reports
- **Streamlit** — deployed interactive web application

## 5. Dashboard Pages

The Power BI report contains three pages:

1. **Overview** — high-level movie performance metrics.
2. **Genre & Movie Analysis** — genre and movie comparisons, including top movies by profit.
3. **Movie Details & Performance** — detailed information for an individual movie, accessed through drill-through.

The report also includes slicers and a drill-through interaction.

## 6. Project Folder Structure

```text
Movie_Ratings_and_Box-Office_Analysis/
│
├── data/
│   ├── raw/
│   ├── clean/
│   │   ├── movies_clean.csv
│   │   └── movie_genres.csv
│   └── movies.db
│
├── app/
│   └── streamlit_app.py
├── notebooks/
├── reports/
│   └── test_results.csv
│
├── sql/
├── src/
├── Tests/
│   └── test_pipeline.py
│
├── movie_box_analysis.pbix
├── requirements.txt
└── README.md
```

## 7. Database Design

The SQLite database is `data/movies.db`. It contains six tables:

- `dim_movie`
- `dim_date`
- `dim_language`
- `dim_genre`
- `fact_movie_performance`
- `bridge_movie_genre`

The fact table stores movie performance measures, while the dimension and bridge tables organize movie, date, language, and genre information.

## 8. How to Run the Project

Run these steps from the project root folder.

### Step 1: Get the project files

Download or clone the project repository and open the project folder.

### Step 2: Install the required Python package

```bash
python -m pip install pandas
```

### Step 3: Check the project data files

Make sure these files are present:

```text
data/clean/movies_clean.csv
data/clean/movie_genres.csv
data/movies.db
```

### Step 4: Run the pipeline tests

In PowerShell or a terminal, run:

```powershell
python -u Tests/test_pipeline.py
```

The test results are written to:

```text
reports/test_results.csv
```

### Step 5: Open the Power BI report

Open `movie_box_analysis.pbix` in Power BI Desktop. Use the report pages, slicers, and drill-through to explore the analysis.

## 9. Data Source

**Dataset name:** [Add the actual dataset name]

**Original source:** [Add the original dataset website and URL]

**Licence:** [Add the dataset licence or usage terms]

The project uses cleaned movie data in CSV format and a SQLite database. The original dataset name, source URL, and licence have not yet been confirmed in this README.

## 10. Assumptions and Limitations

- Missing budget, revenue, runtime, or rating values are treated as unavailable information, not as confirmed real-world values.
- Financial analysis is limited to records for which the relevant financial information is available.
- Revenue and budget values are reported in the currency/unit represented by the source data; confirm the source dataset's currency before interpreting them as USD.
- Dashboard results depend on the completeness and accuracy of the source data.
- The Power BI report is shared through a sign-in-required link. Viewers need a Power BI account and must sign in to access it; it is not publicly viewable without authentication.

## 11. AI Usage

ChatGPT was used as an assistance tool during development for:
- Explaining Python, SQL, SQLite, and Power BI concepts.
- Helping debug and improve project test code.
- Explaining dashboard setup and interactions.
- Structuring and drafting project documentation.

Code and analysis outputs should be reviewed and verified against the actual project files and execution results.

## 12. Demo

**Streamlit web application:** [Open the live Movie Ratings and Box-Office Analysis app](https://movie-ratings-and-box-office-analysis.streamlit.app/)

The Streamlit application is deployed on Streamlit Community Cloud. The live link was tested in an Incognito browser window and opened successfully.

**Power BI report file:** `movie_box_analysis.pbix`

**Power BI report:** [Open the Movie Ratings and Box-Office Analysis report](https://app.powerbi.com/links/o_JaE78iXo?ctid=3ad87f0e-1f93-41bd-94f4-82c37d971c88&pbi_source=linkShare&bookmarkGuid=b6cdf298-43aa-4f89-a26e-55178c855ceb)

**Access requirement:** This Power BI link is not public. Only viewers who have a Power BI account can access the report, and they must sign in first. The account's Publish to web feature is disabled.

## 13. Conclusion

This project brings together Python, Pandas, SQLite, SQL, and Power BI to organize and analyze movie ratings and box-office performance. The matching Python and SQL revenue totals provide a cross-check of the revenue aggregation. The interactive Power BI report allows users to explore overall performance, genre comparisons, and individual movie details.
