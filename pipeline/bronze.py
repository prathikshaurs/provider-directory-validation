"""
BRONZE LAYER — raw ingestion.
Loads all source files into DuckDB exactly as-is (no cleaning).
This is the 'landing zone'. We keep raw copies so we can always
reprocess from the original if our logic changes.
"""
import duckdb

DB = "provider_validation.duckdb"

def run():
    con = duckdb.connect(DB)

    # Each source becomes a bronze_* table. read_csv_auto infers columns.
    # all_varchar=true loads everything as text so messy raw values
    # (blank NPIs, odd formats) never break ingestion. Cleaning is Silver's job.
    sources = {
        "bronze_nppes":     "data/raw/nppes_providers.csv",
        "bronze_directory": "data/raw/provider_directory.csv",
        "bronze_claims":    "data/raw/claims.csv",
        "bronze_exclusions":"data/raw/leie_exclusions.csv",
    }

    for table, path in sources.items():
        con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(f"""
            CREATE TABLE {table} AS
            SELECT * FROM read_csv_auto('{path}', all_varchar=true)
        """)
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:20s} loaded {count:>6} rows")

    con.close()
    print("\nBronze layer complete.")

if __name__ == "__main__":
    run()
