# Sales Analytics Pipeline

A dockerized data pipeline that extracts sales data from CSV, loads it into PostgreSQL, and transforms it with dbt to produce analytical outputs.

## Prerequisites

- **Docker**: Version 20.x or higher
- **Docker Compose**: Version 2.x or higher  
- **Git**: For cloning the repository
- **Available ports**: 5432 (PostgreSQL)

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd <repository-name>
```

### 2. Configure environment variables

Copy the example environment file and update if needed:

```bash
cp .env.example .env
```

The default values in `.env.example` work out of the box. Only change them if you have port conflicts or want different database credentials.

**Required variables:**
- `POSTGRES_DB=sales_analytics`
- `POSTGRES_USER=dataeng`
- `POSTGRES_PASSWORD=changeme_strong_password`
- All schema names (raw, staging, intermediate, marts)

## Running the Pipeline

### Full Pipeline Execution

Run the complete pipeline (extract, load, transform, test):

```bash
bash orchestration/run_pipeline.sh
```

This script will:
1. Start PostgreSQL and wait for it to be ready
2. Run the Python ETL to load raw data
3. Execute dbt transformations (staging → intermediate → marts)
4. Run all data quality tests
5. Print a summary of results

**Expected output:** You should see "Pipeline completed successfully" with a summary showing 51 rows loaded and all tests passing.

### Running Individual Components

If you need to run components separately:

**Start services:**
```bash
docker compose up -d
```

**Run Python ETL only:**
```bash
docker compose exec etl python load.py --csv-path /data/sales_data.csv
```

**Run dbt transformations only:**
```bash
docker compose exec dbt dbt run
```

**Run dbt tests only:**
```bash
docker compose exec dbt dbt test
```

**Stop services:**
```bash
docker compose down
```

**Clean slate (removes all data):**
```bash
docker compose down -v
```

## Running Tests

### Full Test Suite

The pipeline includes 38 tests total (13 pytest + 25 dbt tests).

**Run all tests:**
```bash
# Python tests
docker compose exec etl pytest

# dbt tests  
docker compose exec dbt dbt test
```

### Python Tests (13 tests)

Tests cover ETL validation logic, column name cleaning, and configuration loading.

```bash
docker compose exec etl pytest -v
```

**What's tested:**
- CSV structure validation (empty files, missing columns)
- Column name normalization
- Configuration loading from environment variables
- Basic function contracts

### dbt Tests (25 tests)

Tests validate data quality and business logic across all models.

```bash
docker compose exec dbt dbt test
```

**What's tested:**
- NOT NULL constraints on critical fields
- Unique transaction IDs
- Valid categorical values (region, customer_type, payment_method)
- No negative revenue (custom test)
- Referential integrity

**See individual test results:**
```bash
docker compose exec dbt dbt test --store-failures
```

## Troubleshooting

### PostgreSQL won't start

**Symptom:** `postgres` service exits immediately or healthcheck fails

**Solutions:**
- Port 5432 already in use: Change `POSTGRES_PORT` in `.env` and update `docker-compose.yml` ports mapping
- Permission issues: Run `docker compose down -v` to remove old volumes
- Check logs: `docker compose logs postgres`

### ETL fails with "connection refused"

**Symptom:** Python script can't connect to database

**Solutions:**
- Postgres isn't ready yet: The `run_pipeline.sh` script handles this, but if running manually, wait 10 seconds after `docker compose up`
- Wrong credentials: Verify `.env` matches what's in `docker-compose.yml`
- Network issues: Run `docker compose down` and `docker compose up -d` to recreate networks

### dbt tests fail

**Symptom:** `dbt test` shows failures

**Expected behavior:** All 25 tests should pass with the provided sample data.

**If tests fail:**
- Check that Python ETL completed successfully (51 rows in raw.sales_raw)
- Verify dbt models ran: `docker compose exec dbt dbt run`
- Check specific failure: `docker compose exec dbt dbt test --store-failures` then query the failures table
- Nuclear option: `docker compose down -v && bash orchestration/run_pipeline.sh`

### Pipeline runs but no data in marts

**Symptom:** `fct_daily_sales` table is empty or has fewer rows than expected

**Solutions:**
- Check that staging model filtered out bad rows: `docker compose exec dbt dbt run --select stg_sales`
- Inspect the data: Connect to Postgres on localhost:5432 and query `marts.fct_daily_sales`
- Check logs: `docker compose logs dbt`

### "Port 5432 already in use"

**Solution:**

Either stop the conflicting service or change the port mapping in `docker-compose.yml`:

```yaml
ports:
  - "5433:5432"  # Maps container's 5432 to host's 5433
```

## Next Steps

- **See ARCHITECTURE.md** for design decisions, data flow, and schema layer rationale
- **See TESTING.md** for detailed test coverage and testing strategy
- **Explore dbt docs:** Run `docker compose exec dbt dbt docs generate && dbt docs serve` to view the full data lineage and documentation

## Project Structure

```
.
├── data/
│   └── sales_data.csv
├── dbt/
│   ├── models/
│   │   ├── staging/            # Type casting, normalization
│   │   ├── intermediate/       # Business logic, calculations
│   │   └── marts/              # Final analytical tables
│   ├── tests/                  # Custom dbt tests
│   └── dbt_project.yml         # dbt configuration
├── etl/
│   ├── load.py                 # Load CSV to postgres
│   ├── transform.py            # Column name cleaning
│   ├── tests/                  # pytest unit tests
│   └── requirements.txt        # Python dependencies
├── orchestration/
│   └── run_pipeline.sh         # Full pipeline execution script
├── docker-compose.yml          # Service orchestration
├── .env.example                # Environment variables template
└── README.md                   # This file
```