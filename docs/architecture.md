# Architecture

```mermaid
flowchart LR
    subgraph Sources["Data Sources"]
        A[NPPES Registry<br/>real, federal]
        B[OIG LEIE Exclusions<br/>real, federal]
        C[Provider Directory<br/>synthetic, no PHI]
        D[Claims Feed<br/>synthetic, no PHI]
    end

    subgraph Bronze["Bronze — Raw Ingestion"]
        E[(bronze_* tables<br/>loaded as-is)]
    end

    subgraph Silver["Silver — Clean & Standardize"]
        F[(silver_* tables<br/>typed, normalized keys)]
    end

    subgraph Validation["Federated Validation Framework"]
        G{6 configurable rules<br/>cross-source checks}
    end

    subgraph Gold["Gold — Business Output"]
        H[(gold_provider_scores<br/>trust score + action)]
    end

    A --> E
    B --> E
    C --> E
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I[Looker / Tableau<br/>BI consumption]
```

## Layer responsibilities

- **Bronze:** land raw data safely as text; never lose the original.
- **Silver:** trim, uppercase, normalize NPIs, convert blanks to NULL, type dates/numbers.
- **Validation:** federated rules cross-reference each listing against NPPES, OIG, and claims.
- **Gold:** weighted trust score (0–100) and a REMOVE / REVIEW / KEEP action per listing.

## Production mapping

| This demo | Production equivalent at scale |
|-----------|-------------------------------|
| DuckDB | Snowflake / Redshift / Trino |
| Local CSV | S3 + Apache Iceberg tables |
| Python scripts | dbt models + Spark jobs |
| Manual run | Airflow / Argo orchestration |
