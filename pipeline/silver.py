"""
SILVER LAYER (cleaning and standardizing the data)
bronze_ tables -> silver_* tables:
  - trimmed, uppercased names (so that matching is reliable)
  - NPIs normalized to clean 10-char strings (leading zeros preserved since they are IDs)
  - blanks converted to NULL (so 'missing' is explicit, not an empty string)
  - typed columns where it matters (dates, numbers)
"""
import duckdb

DB = "provider_validation.duckdb"

def run():
    con = duckdb.connect(DB)

    # silver_nppes: the source of truth
    con.execute("DROP TABLE IF EXISTS silver_nppes")
    con.execute("""
        CREATE TABLE silver_nppes AS
        SELECT
            TRIM(npi)                          AS npi,
            UPPER(TRIM(first_name))            AS first_name,
            UPPER(TRIM(last_name))             AS last_name,
            UPPER(TRIM(city))                  AS city,
            UPPER(TRIM(state))                 AS state,
            TRIM(postal_code)                  AS postal_code
        FROM bronze_nppes
        WHERE npi IS NOT NULL AND TRIM(npi) <> ''
    """)

    # silver_directory: the data we validate
    con.execute("DROP TABLE IF EXISTS silver_directory")
    con.execute("""
        CREATE TABLE silver_directory AS
        SELECT
            TRIM(directory_id)                 AS directory_id,
            TRIM(npi)                          AS npi,
            UPPER(TRIM(first_name))            AS first_name,
            UPPER(TRIM(last_name))             AS last_name,
            UPPER(TRIM(address))               AS address,
            UPPER(TRIM(city))                  AS city,
            UPPER(TRIM(state))                 AS state,
            TRIM(zip)                          AS zip,
            NULLIF(TRIM(phone), '')            AS phone,
            UPPER(TRIM(accepting_new_patients)) AS accepting_new_patients
        FROM bronze_directory
    """)

    # silver_claims: for typed dates and amounts
    con.execute("DROP TABLE IF EXISTS silver_claims")
    con.execute("""
        CREATE TABLE silver_claims AS
        SELECT
            TRIM(claim_id)                     AS claim_id,
            TRIM(npi)                          AS npi,
            TRY_CAST(service_date AS DATE)     AS service_date,
            TRY_CAST(claim_amount AS DOUBLE)   AS claim_amount
        FROM bronze_claims
        WHERE npi IS NOT NULL AND TRIM(npi) <> ''
    """)

    # silver_exclusions: the OIG blacklist, normalized for matching
    # Real NPIs only (drop the 0000000000 placeholders for NPI matching),
    # but keeps names so it can also match by name
    con.execute("DROP TABLE IF EXISTS silver_exclusions")
    con.execute("""
        CREATE TABLE silver_exclusions AS
        SELECT
            NULLIF(TRIM(npi), '0000000000')    AS npi,
            UPPER(TRIM(firstname))             AS first_name,
            UPPER(TRIM(lastname))              AS last_name,
            UPPER(TRIM(busname))               AS business_name,
            TRIM(excltype)                     AS exclusion_type,
            TRY_CAST(excldate AS VARCHAR)      AS exclusion_date
        FROM bronze_exclusions
    """)

    # quick report
    for t in ["silver_nppes","silver_directory","silver_claims","silver_exclusions"]:
        c = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t:20s} {c:>6} rows")

    con.close()
    print("\nSilver layer complete.")

if __name__ == "__main__":
    run()