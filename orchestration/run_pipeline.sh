#!/bin/bash
set -euo pipefail

# Disable MSYS path conversion on Windows (Git Bash)
# Without this, /data/sales_data.csv gets converted to C:/Program Files/Git/data/...
export MSYS_NO_PATHCONV=1

# Color codes for output
RED='\033[0;31m'

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Sales Pipeline Orchestration${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Start Postgres and wait for healthy
echo -e "${YELLOW}[1/5] Starting PostgreSQL...${NC}"
docker compose up -d postgres

# Wait for Postgres to be healthy (check every 2 seconds, timeout after 30 seconds)
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
TIMEOUT=30
ELAPSED=0
until docker compose exec -T postgres pg_isready -U ${POSTGRES_USER:-dataeng} -d ${POSTGRES_DB:-sales_analytics} > /dev/null 2>&1; do
    if [ $ELAPSED -ge $TIMEOUT ]; then
        echo -e "${RED}ERROR: PostgreSQL failed to start within ${TIMEOUT} seconds${NC}"
        exit 1
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done
echo -e "${GREEN}PostgreSQL is ready${NC}"
echo ""

# Step 2: Run Python ETL
echo -e "${YELLOW}[2/5] Running Python ETL...${NC}"
docker compose run --rm etl python load.py --csv-path /data/sales_data.csv

if [ $? -eq 0 ]; then
    echo -e "${GREEN}ETL completed successfully${NC}"
else
    echo -e "${RED}ERROR: ETL failed${NC}"
    exit 1
fi
echo ""

# Step 3: Verify raw data exists
echo -e "${YELLOW}[3/5] Verifying raw data...${NC}"
RAW_COUNT=$(docker compose exec -T postgres psql -U ${POSTGRES_USER:-dataeng} -d ${POSTGRES_DB:-sales_analytics} -t -c "SELECT COUNT(*) FROM raw.sales_raw;" | tr -d ' ')

if [ "$RAW_COUNT" -eq 0 ]; then
    echo -e "${RED}ERROR: No data found in raw.sales_raw${NC}"
    exit 1
fi
echo -e "${GREEN}Found ${RAW_COUNT} rows in raw.sales_raw${NC}"
echo ""

# Step 4: Run dbt models
echo -e "${YELLOW}[4/5] Building dbt models...${NC}"
docker compose run --rm dbt dbt run

if [ $? -eq 0 ]; then
    echo -e "${GREEN}dbt models built successfully${NC}"
else
    echo -e "${RED}ERROR: dbt run failed${NC}"
    exit 1
fi
echo ""

# Step 5: Run dbt tests
echo -e "${YELLOW}[5/5] Running dbt tests...${NC}"
docker compose run --rm dbt dbt test

if [ $? -eq 0 ]; then
    echo -e "${GREEN}All dbt tests passed${NC}"
else
    echo -e "${RED}ERROR: dbt tests failed${NC}"
    exit 1
fi
echo ""

# Final summary
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Pipeline completed successfully!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Summary:"
echo "  - Raw rows loaded: ${RAW_COUNT}"
echo "  - dbt models: 3 built"
echo "  - dbt tests: All passed"
echo ""