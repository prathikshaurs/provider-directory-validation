"""
FEDERATED VALIDATION FRAMEWORK
Each rule is a small, independent function that flags directory listings
by cross-referencing an authoritative source. Rules are registered in a
list, so adding/removing a check is a one-line change (that's the
'framework', not a one-off script). Results feed a per-listing trust score.
"""
import duckdb

DB = "provider_validation.duckdb"

# ---- Each rule returns a SQL boolean expression that is TRUE when the
#      listing FAILS that rule. Keeping rules as data (a list) is what
#      makes this a configurable framework. ----
RULES = [
    {
        "name": "invalid_npi",
        "severity": "high",
        "description": "NPI not found in the federal NPPES registry",
        "flag_sql": "n.npi IS NULL",
    },
    {
        "name": "excluded_provider",
        "severity": "critical",
        "description": "Provider appears on the OIG exclusions (LEIE) list",
        "flag_sql": "e.npi IS NOT NULL",
    },
    {
        "name": "ghost_no_claims",
        "severity": "high",
        "description": "No claims activity — provider may not be practicing",
        "flag_sql": "c.claim_count IS NULL OR c.claim_count = 0",
    },
    {
        "name": "state_mismatch",
        "severity": "medium",
        "description": "Directory state differs from NPPES registry state",
        "flag_sql": "n.npi IS NOT NULL AND d.state <> n.state",
    },
    {
        "name": "missing_phone",
        "severity": "low",
        "description": "No phone number — member cannot contact provider",
        "flag_sql": "d.phone IS NULL",
    },
]

def run():
    con = duckdb.connect(DB)

    # Build a base table that joins each directory listing to all sources ONCE.
    # LEFT JOINs mean 'keep every directory row, attach source info if it exists'.
    con.execute("DROP TABLE IF EXISTS validation_base")
    con.execute("""
        CREATE TABLE validation_base AS
        SELECT
            d.*,
            n.npi AS nppes_npi,
            n.state AS nppes_state,
            e.npi  AS excl_npi,
            c.claim_count
        FROM silver_directory d
        LEFT JOIN silver_nppes n
               ON d.npi = n.npi
        LEFT JOIN (
            SELECT npi FROM silver_exclusions WHERE npi IS NOT NULL GROUP BY npi
        ) e ON d.npi = e.npi
        LEFT JOIN (
            SELECT npi, COUNT(*) AS claim_count
            FROM silver_claims GROUP BY npi
        ) c ON d.npi = c.npi
    """)

    # Apply each rule as its own boolean column: 1 = failed that check.
    # We re-alias the joined columns so the rule SQL reads naturally.
    flag_cols = []
    for r in RULES:
        sql = (r["flag_sql"]
               .replace("n.npi", "nppes_npi")
               .replace("n.state", "nppes_state")
               .replace("e.npi", "excl_npi")
               .replace("c.claim_count", "claim_count")
               .replace("d.state", "state")
               .replace("d.phone", "phone"))
        flag_cols.append(f"CASE WHEN {sql} THEN 1 ELSE 0 END AS flag_{r['name']}")

    con.execute("DROP TABLE IF EXISTS validation_flags")
    con.execute(f"""
        CREATE TABLE validation_flags AS
        SELECT *, {', '.join(flag_cols)}
        FROM validation_base
    """)

    # Print a summary: how many listings failed each rule.
    print("Validation results by rule:")
    print(f"  {'RULE':22s} {'SEVERITY':9s} FAILED")
    for r in RULES:
        failed = con.execute(
            f"SELECT SUM(flag_{r['name']}) FROM validation_flags"
        ).fetchone()[0] or 0
        print(f"  {r['name']:22s} {r['severity']:9s} {failed:>5}")

    total = con.execute("SELECT COUNT(*) FROM validation_flags").fetchone()[0]
    clean = con.execute(f"""
        SELECT COUNT(*) FROM validation_flags
        WHERE {' + '.join('flag_'+r['name'] for r in RULES)} = 0
    """).fetchone()[0]
    print(f"\n  {clean}/{total} listings passed ALL checks "
          f"({100*clean/total:.1f}% clean)")

    con.close()
    print("Validation complete.")

if __name__ == "__main__":
    run()
