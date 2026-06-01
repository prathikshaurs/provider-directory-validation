"""
BRONZE LAYER (raw ingestion)
Source files -> DuckDB
"""
import duckdb

DB = "provider_validation.duckdb"

def run():
    con = duckdb.connect(DB)

    # Each source = bronze_ table
    # all_varchar=true - to load everything as text to avoid breaking ingestion
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