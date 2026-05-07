# Design Decisions

This document records every major design decision in the pipeline with rationale, alternatives, and trade-offs. Use this to prepare for "why did you do it this way?" questions.

---

## Python vs. dbt Boundary

**Decision:** Python handles structural validation and loading only. dbt handles all semantic transformations.

**Rationale:**
- SQL is better for data transformation (declarative, database-optimized, easier to test)
- Python is better for I/O (file handling, error management, orchestration)
- Preserves raw data in database for debugging (VARCHAR preserves "Error", "10%", etc.)
- Separation of concerns: load failures vs. transformation failures are different problems
- dbt's testing framework beats custom Python data quality checks

**Alternatives considered:**
1. **Clean everything in Python, simple dbt:** Would lose raw data audit trail, make Python loader more complex, harder to test transformations
2. **Clean everything in dbt, minimal Python:** Would require dbt seeds or COPY commands, less portable, no validation before load
3. **Pandas for transformations:** Harder to version control, test, and document than SQL

**Trade-off accepted:** Extra layer of complexity (two tools instead of one), but gains testability and clear separation of concerns.

**Interview question this answers:** "Why didn't you just do all the cleaning in pandas?"

---

## Schema Layer Architecture (4 layers)

**Decision:** raw → staging → intermediate → marts

**Rationale:**
- **Raw:** Preserve source exactly for debugging (all VARCHAR)
- **Staging:** Clean and type (one place for all normalization logic)
- **Intermediate:** Business logic and derived fields (revenue calculations separate from cleaning)
- **Marts:** Aggregated for reporting (clear grain, pre-computed for performance)

**Alternatives considered:**
1. **Two layers (raw → marts):** Would mix cleaning, business logic, and aggregation in one model. Hard to test and maintain.
2. **Three layers (raw → staging → marts):** Where do revenue calculations go? In staging, they mix with cleaning. In marts, aggregations become complex.
3. **Five layers (add metrics layer):** Overkill for this dataset size and complexity.

**Trade-off accepted:** More models to maintain, but each has a clear single purpose.

**Interview question this answers:** "Why not just go raw → staging → marts?"

---

## Discount Column Normalization

**Decision:** Strip "%", if value > 1 then divide by 100, store as decimal [0,1]

**Rationale:**
- Source has "10%", "10", "0.10", "5" for the same concept
- We need a single canonical representation for calculations
- Decimal [0,1] is the standard for rates (0.10 = 10%)
- If someone wrote "10" meaning 10%, value > 1 tells us to convert

**Implementation (in stg_sales.sql):**
```sql
case
    when regexp_replace(trim(discount), '%', '') ~ '^\d+\.?\d*$' then
        case
            when cast(regexp_replace(trim(discount), '%', '') as numeric) <= 1 
                then cast(regexp_replace(trim(discount), '%', '') as numeric)
            else cast(regexp_replace(trim(discount), '%', '') as numeric) / 100
        end
    else null
end as discount
```

**Alternatives considered:**
1. **Assume everything is percentage, divide all by 100:** Would break "0.05" (becomes 0.0005)
2. **Only accept one format, reject others:** Would lose valid data
3. **Store as percentage (10.0 for 10%):** Non-standard, confusing in calculations

**Trade-off accepted:** Complex logic in SQL, but handles all source variations correctly.

**Interview question this answers:** "How did you handle the inconsistent discount formats?"

---

## Date Parsing Strategy

**Decision:** Handle 7 different formats with regex detection, parse with to_date(), NULL on failure

**Formats handled:**
- ISO: 2023-01-15, 2023/01/17
- US slash: 1/16/2023, 01/20/23
- European dash: 22-01-2023
- European dot: 29.01.2023, 6.2.2023
- Month name: 26-Jan-23

**Rationale:**
- Source data has inconsistent date formats (probably from Excel or manual entry)
- We need to parse all valid dates, not just one format
- Regex pattern matching + to_date() is more reliable than casting
- Ambiguous dates (01/02/2023) default to MM/DD/YYYY (US convention, dayfirst=False)

**Implementation:** Pattern match first, then parse with appropriate format string

**Alternatives considered:**
1. **Python dateutil.parser:** Would require cleaning in Python, loses raw data
2. **Accept only one format:** Would lose 80% of valid dates
3. **Manual parsing with string functions:** More fragile than to_date()

**Trade-off accepted:** Complex SQL, but preserves maximum data and handles real-world messiness.

**Interview question this answers:** "Your date parsing is pretty complex. Why not use a library?"

---

## Store ID Normalization

**Decision:** Extract trailing digits, prefix with "STORE_", result: STORE_005, STORE_006, STORE_007

**Rationale:**
- Source has: "Store_005", "STORE_005", "store_005", "StoreID_005", "Store-005", "Store 005"
- We need canonical format for grouping and joins
- Business logic cares about the number (005), not the prefix variation
- STORE_NNN is readable and consistent

**Implementation:**
```sql
'STORE_' || regexp_replace(trim(store_id), '.*?(\d+)$', '\1') as store_id
```

**Alternatives considered:**
1. **Leave as-is, use UPPER():** Still have "STORE_005" vs "STOREID_005"
2. **Just extract number:** "005" is less readable than "STORE_005"
3. **Hardcode mapping:** Doesn't scale if new stores added

**Trade-off accepted:** Assumes store ID always ends with digits (true for this dataset).

**Interview question this answers:** "Why normalize store IDs instead of just uppercasing them?"

---

## Region Normalization

**Decision:** UPPER() + replace spaces with underscores

**Rationale:**
- Source has: "West", "west", "WEST", "North West", "North East"
- SQL grouping is case-sensitive: "West" ≠ "west"
- Spaces in identifiers are annoying (need quotes in SQL)
- NORTH_WEST is consistent and SQL-friendly

**Alternatives considered:**
1. **Leave with spaces:** Would need quotes: WHERE region = 'North West'
2. **Use region codes (NW, NE):** Loses readability
3. **Create dimension table:** Overkill for 6 regions

**Trade-off accepted:** NORTH_WEST is less natural than "North West" but more SQL-friendly.

**Interview question this answers:** "Why underscores instead of spaces in region names?"

---

## Customer Type Mapping

**Decision:** Map "RegularCustomer" → "Regular", keep Premier/Premium distinct

**Rationale:**
- Source has: "Regular", "RegularCustomer", "Premium", "Premier"
- "RegularCustomer" is clearly a typo/variant of "Regular"
- Premier vs. Premium could be distinct tiers OR typos
- Without business context, we preserve both and let analysts decide

**Alternatives considered:**
1. **Merge Premier and Premium:** Might lose real business distinction
2. **Leave RegularCustomer as-is:** Creates artificial segmentation
3. **Ask business stakeholder:** Not available for this assignment

**Trade-off accepted:** May have a false distinction (Premier vs. Premium) but preserves potential business logic.

**Interview question this answers:** "Why didn't you merge Premier and Premium?"

---

## Payment Method Mapping

**Decision:** Map "Debit" → "Debit Card", keep others as-is

**Rationale:**
- Source has: "Debit" and "Debit Card" for same concept
- "Credit Card" and "Cash" and "Apple Pay" are unambiguous
- Standardizing to "Debit Card" matches "Credit Card" pattern

**Alternatives considered:**
1. **Leave both:** Creates false segmentation in analysis
2. **Map to "Debit":** Inconsistent with "Credit Card"

**Trade-off accepted:** Assumes "Debit" and "Debit Card" are the same (true in real world).

**Interview question this answers:** "How did you handle payment methods?"

---

## NULL Handling Strategy

**Decision:** Convert "na", "error", empty string, whitespace to SQL NULL

**Rationale:**
- Source has literal "na" strings and "error" values (e.g., in price field)
- SQL NULL is the standard for "missing data"
- Empty strings and whitespace-only are meaningless values
- Downstream calculations need to treat these as missing, not as strings

**Implementation:** Check for these values in CASE statements before casting

**Alternatives considered:**
1. **Keep as-is:** Would create type casting errors ("na" can't cast to INTEGER)
2. **Use sentinel values (-1, "UNKNOWN"):** Confuses "missing" with "known to be -1"
3. **Filter out in Python:** Would lose the data quality signal

**Trade-off accepted:** Verbose CASE statements, but correct NULL handling.

**Interview question this answers:** "How did you decide what counts as NULL?"

---

## Idempotency Strategy

**Decision:** Full refresh (DELETE + INSERT) on every run

**Rationale:**
- Source is a static CSV (doesn't grow)
- 51 rows rebuild in <1 second
- Simpler to reason about: every run produces identical output
- No watermark tracking needed
- Transaction ensures atomicity (all-or-nothing)

**Alternatives considered:**
1. **Append-only with timestamp:** Would create duplicates, need deduplication logic
2. **Incremental with CDC:** Massive overkill for static data
3. **MERGE/UPSERT:** More complex, no benefit for static source

**Trade-off accepted:** Not production-ready for growing datasets, but perfect for this use case.

**Interview question this answers:** "Why full refresh instead of incremental?"

---

## Missing Transaction ID Handling

**Decision:** Allow NULL transaction IDs, test uniqueness only where NOT NULL

**Rationale:**
- Source has one row with missing transaction_id (blank value)
- We preserve the row (it has valid sales data)
- dbt unique test scoped to non-NULL values: `where: "transaction_id IS NOT NULL"`
- Downstream aggregations don't depend on transaction_id

**Alternatives considered:**
1. **Filter out the row:** Would lose valid sales data
2. **Generate surrogate key:** Would create fake identifier
3. **Fail the pipeline:** Too strict for data quality issue that doesn't affect analysis

**Trade-off accepted:** Analytics on transaction-grain would exclude this row, but daily aggregates include it.

**Interview question this answers:** "What did you do about the missing transaction ID?"

---

## Testing Strategy

**Decision:** 13 pytest (Python unit tests) + 25 dbt tests (data quality)

**Python tests:**
- Test individual functions (validate_structure, clean_column_names, load_config)
- Use mocks (no real database needed)
- Fast feedback (<1 second)

**dbt tests:**
- Schema tests (not_null, unique, accepted_values)
- Relationships (not implemented yet, would be for star schema)
- Custom tests (no negative revenue)

**Rationale:**
- Python tests catch logic errors before data hits database
- dbt tests catch data quality issues after transformations
- Separation of concerns: code correctness vs. data correctness

**Alternatives considered:**
1. **Integration tests (Python → Postgres):** Would test Docker networking, not our logic
2. **E2E tests:** Already covered by running full pipeline manually
3. **More granular dbt tests:** Could test every column, but diminishing returns

**Trade-off accepted:** No integration tests (deliberate gap, tested manually).

**Interview question this answers:** "Why didn't you write integration tests?"

---

## Technology Choices

### Docker Compose (not Kubernetes)
**Why:** Ensures version consistency, easy local development, one command to start everything.
**Trade-off:** Not production orchestration, but perfect for local development.

### PostgreSQL (not SQLite or DuckDB)
**Why:** Industry standard, production-like, strong SQL feature set, what the prompt suggested.
**Trade-off:** Heavier than SQLite, but more realistic.

### dbt (not raw SQL scripts)
**Why:** Testing framework, documentation generation, dependency management, lineage.
**Trade-off:** Learning curve, but industry standard for analytics.

### Python + pandas (not dbt seeds)
**Why:** Validation logic, error handling, scalable (seeds don't work for large files).
**Trade-off:** Extra service in Docker, but clean separation of concerns.

---

## What We Explicitly Did NOT Do

**Star schema:** Could build dim_store, dim_product, dim_date, fct_sales. Didn't because:
- Prompt didn't require it
- Only 3 stores, 1 product category → dimensions would have 3 rows
- Overkill for this dataset
- Would add in Pass 2 if needed

**Incremental models:** Could make fct_daily_sales incremental with `is_incremental()`. Didn't because:
- Static source data
- Full refresh is simpler
- Would add if source was growing

**Secrets management:** Could use AWS Secrets Manager, Vault, etc. Didn't because:
- Local development only
- .env is standard for local
- Would add for production

**Orchestration platform:** Could use Airflow, Dagster, Prefect. Didn't because:
- Bash script is sufficient for linear pipeline
- No scheduling needed (one-time load)
- Would add for production

---

## Questions to Prepare For

**"Walk me through what happens when I run the pipeline."**
1. Docker Compose starts Postgres, waits for healthy
2. Python ETL reads CSV (51 rows), validates structure, cleans column names, loads to raw.sales_raw as VARCHAR
3. dbt runs staging model (cleans, types, normalizes)
4. dbt runs intermediate model (revenue calculations, date dimensions)
5. dbt runs marts model (daily aggregates)
6. dbt runs 25 tests, all pass
7. Script prints summary

**"What if the CSV had 1 billion rows?"**
- Python: Stream CSV in chunks (pandas.read_csv chunksize), batch insert
- dbt: Switch to incremental models, partition by date
- Postgres: Probably switch to Snowflake/BigQuery for warehouse scale

**"What if a new column appears in the source?"**
- Python validation would fail (unexpected column warning)
- Raw layer would ignore it (only loads expected columns)
- Add to EXPECTED_COLUMNS in Python
- Add to stg_sales.sql if needed downstream

**"What's the worst decision you made?"**
Be ready to critique your own work. Example: "I'd handle date parsing more robustly with a lookup table of format patterns rather than nested CASE statements."