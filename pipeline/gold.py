"""
GOLD LAYER — business-ready output.
Converts raw validation flags into:
  - a weighted trust_score (0-100) per listing
  - a recommended_action (REMOVE / REVIEW / KEEP)
  - a human-readable list of which issues were found
This is the table a directory/quality team would actually consume.
"""
import duckdb

DB = "provider_validation.duckdb"

# Severity weights: how many points each failed check deducts.
# Critical issues (compliance) hurt far more than cosmetic ones.
WEIGHTS = {
    "excluded_provider": 60,   # critical — compliance/legal risk
    "invalid_npi":       40,   # high — provider doesn't exist in registry
    "ghost_no_claims":   25,   # high — likely not practicing
    "state_mismatch":    15,   # medium — stale location
    "missing_phone":     10,   # low — can't contact
}

def run():
    con = duckdb.connect(DB)

    # Build the score: start at 100, subtract each failed rule's weight,
    # floor at 0. GREATEST(...,0) prevents negative scores.
    deductions = " + ".join(
        f"flag_{rule} * {pts}" for rule, pts in WEIGHTS.items()
    )

    # A readable issue list: concatenate the names of failed checks.
    issue_parts = " || ".join(
        f"CASE WHEN flag_{rule}=1 THEN '{rule}; ' ELSE '' END"
        for rule in WEIGHTS
    )

    con.execute("DROP TABLE IF EXISTS gold_provider_scores")
    con.execute(f"""
        CREATE TABLE gold_provider_scores AS
        SELECT
            directory_id,
            npi,
            first_name,
            last_name,
            city,
            state,
            GREATEST(100 - ({deductions}), 0)   AS trust_score,
            TRIM(TRAILING '; ' FROM ({issue_parts})) AS issues_found,
            CASE
                WHEN GREATEST(100 - ({deductions}),0) < 40 THEN 'REMOVE'
                WHEN GREATEST(100 - ({deductions}),0) < 80 THEN 'REVIEW'
                ELSE 'KEEP'
            END                                  AS recommended_action
        FROM validation_flags
    """)

    # Summary by recommended action
    print("Gold layer — recommended actions:")
    rows = con.execute("""
        SELECT recommended_action, COUNT(*) AS n,
               ROUND(AVG(trust_score),1) AS avg_score
        FROM gold_provider_scores
        GROUP BY recommended_action
        ORDER BY avg_score
    """).fetchdf()
    print(rows.to_string(index=False))

    # Show a few of the worst offenders
    print("\nLowest-trust listings (worst 5):")
    worst = con.execute("""
        SELECT directory_id, trust_score, recommended_action, issues_found
        FROM gold_provider_scores
        ORDER BY trust_score ASC
        LIMIT 5
    """).fetchdf()
    print(worst.to_string(index=False))

    con.close()
    print("\nGold layer complete.")

if __name__ == "__main__":
    run()
