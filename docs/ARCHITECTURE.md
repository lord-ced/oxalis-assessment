# Architecture Documentation

## Data Flow

```
sales_data.csv
    ↓
Python ETL (load.py)
    ↓
raw.sales_raw (all VARCHAR)
    ↓
dbt: stg_sales (clean & type)
    ↓
staging.stg_sales
    ↓
dbt: int_sales_enriched (business logic)
    ↓
intermediate.int_sales_enriched
    ↓
dbt: fct_daily_sales (aggregate)
    ↓
marts.fct_daily_sales
```

## Schema Layers

### Raw Layer (`raw.sales_raw`)
**What:** Source data loaded as-is, all columns VARCHAR.

**Why:** Preserves source fidelity for debugging. If the CSV has "Error" in a price field, we want to see it here before it gets cleaned.

### Staging Layer (`staging.stg_sales`)
**What:** Clean and type the data. Parse dates, normalize store IDs and regions, convert discount formats, map customer types, cast to proper types.

**Why:** All downstream models can assume clean, typed data. New cleaning rules go here without touching business logic.

### Intermediate Layer (`intermediate.int_sales_enriched`)
**What:** Business logic and derived fields. Calculate gross revenue, discount amounts, net revenue. Extract date dimensions. Filter out rows that can't participate in calculations.

**Why:** Separates "how we clean data" (staging) from "what the data means" (intermediate). Makes revenue logic testable and auditable.

### Marts Layer (`marts.fct_daily_sales`)
**What:** Aggregated analytics table. Daily grain by store/region/customer. Transaction counts, revenue totals, average basket size.

**Why:** End users query this layer. Clear grain definition. Materialized as table for performance.

## Key Architectural Decision: Python vs. dbt Boundary

**Python handles:**
- Structural validation (does CSV have expected columns?)
- Column name cleaning (messy names to snake_case)
- Database I/O (load to raw as VARCHAR)
- No semantic transformations

**dbt handles:**
- All type casting
- All data cleaning
- All business logic
- All aggregations
- All data quality tests

**Why this split:**
- SQL is better for data transformation (declarative, database-optimized)
- Python is better for I/O and orchestration (error handling, file systems)
- Preserves raw data in database for debugging
- dbt's testing framework beats custom Python assertions
- Clear separation: load failures vs. transformation failures

**Trade-off:** Could have parsed dates in Python for simpler dbt. Chose not to because it would make Python loader more complex and lose the raw data audit trail.

## Technology Choices

**Docker Compose:** Version consistency across environments.

**PostgreSQL:** Industry standard, strong SQL support, open source.

**dbt:** Analytics transformation standard. Built-in testing, docs, lineage.

**Python + pandas:** CSV processing standard. SQLAlchemy for database connections.

## Idempotency

Full refresh on every run:
- Python: DELETE then INSERT (in transaction)
- dbt: Rebuild all models from scratch

Works for this project (static CSV, 51 rows). Production would use incremental processing with watermarks.

## What's Not Here (Deliberately)

This is a working pipeline, not a production platform. Missing by design:
- Secrets management (using .env for simplicity)
- Incremental processing (full refresh is simpler)
- Production orchestrator (using bash script)
- CI/CD (not in scope)
- Star schema (could add in Pass 2)
- Monitoring/alerting (not needed for static data)