"""
ETL loader: reads CSV, validates structure, loads to raw schema.

This script handles the extraction and loading phases of the pipeline.
No semantic cleaning happens here - all business logic and type casting
happens downstream in dbt. This loader's job is to:
1. Verify the CSV is structurally sound (correct columns, parseable)
2. Load it into raw.sales_raw with all columns as TEXT
3. Verify the load succeeded

Design decisions:
- All columns loaded as VARCHAR/TEXT to preserve source fidelity
- Transaction-wrapped load for atomicity (all-or-nothing)
- Truncate-and-load strategy (full refresh each run)
- Structured logging via the logging module
- Config from environment variables only (no hardcoded credentials)
"""

import logging
import sys
import os
from typing import Dict, Optional
import argparse

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


# Expected columns in the source CSV (order doesn't matter, but names must match)
EXPECTED_COLUMNS =[
    'date',
    'store ID',
    'PRODUCT_NAME',
    ' quantity',       # Note: leading space in source
    'Price',
    'customer_type',
    'Payment Method',
    'Transaction_ID',
    ' discount%',      # Note: leading space in source
    'region'
]


def load_config() -> Dict[str, str]:
    """
    Load database configuration from environment variables.
    
    Fails fast if any required variable is missing, listing all missing
    variables at once for better developer experience.
    
    Returns:
        Dict with keys: POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, 
                        POSTGRES_USER, POSTGRES_PASSWORD
    
    Raises:
        ValueError: If any required environment variable is missing
    """
    required_vars = [
        'POSTGRES_HOST',
        'POSTGRES_PORT', 
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD'
    ]
    
    config = {}
    missing = []
    
    for var in required_vars:
        value = os.getenv(var)
        if value is None:
            missing.append(var)
        else:
            config[var] = value
    
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}"
        )
    
    return config


def read_csv(path: str) -> pd.DataFrame:
    """
    Read CSV file with all columns as strings to preserve source values.
    
    We don't parse dates, cast types, or clean values here. That's dbt's job.
    Loading everything as strings ensures we can land the data even if there
    are format inconsistencies, and we can debug from the raw layer.
    
    Args:
        path: File path to the CSV
    
    Returns:
        DataFrame with all columns as string dtype
    
    Raises:
        FileNotFoundError: If CSV doesn't exist
        pd.errors.EmptyDataError: If CSV is empty
        pd.errors.ParserError: If CSV is malformed
    """
    logger.info(f"Reading CSV from: {path}")
    
    # dtype=str forces all columns to be read as strings
    # keep_default_na=False prevents pandas from converting "NA" strings to NaN
    df = pd.read_csv(path, dtype=str, keep_default_na=False)
    
    logger.info(f"Read {len(df)} rows from CSV")
    
    return df


def validate_structure(df: pd.DataFrame) -> None:
    """
    Validate that the DataFrame has the expected structure.
    
    This is a structural check only, not a data quality check:
    - Are all expected columns present?
    - Is the DataFrame non-empty?
    
    We don't validate data values here (nulls, formats, ranges). That's dbt's job.
    
    Args:
        df: DataFrame to validate
    
    Raises:
        ValueError: If structure validation fails
    """
    logger.info("Validating CSV structure")
    
    # Check for empty DataFrame
    if len(df) == 0:
        raise ValueError("CSV file is empty (no data rows)")
    
    # Check for missing columns
    df_columns = set(df.columns)
    expected_columns = set(EXPECTED_COLUMNS)
    
    missing = expected_columns - df_columns
    if missing:
        raise ValueError(
            f"CSV is missing required columns: {', '.join(sorted(missing))}"
        )
    
    # Check for extra columns (warning only, not a failure)
    extra = df_columns - expected_columns
    if extra:
        logger.warning(
            f"CSV contains unexpected columns (will be ignored): {', '.join(sorted(extra))}"
        )
    
    logger.info(f"Structure validation passed: {len(df)} rows, {len(df.columns)} columns")


def connect_db(config: Dict[str, str]) -> Engine:
    """
    Create a SQLAlchemy engine for Postgres connection.
    
    The engine provides connection pooling and handles reconnection logic.
    We don't open a connection here, just create the engine. Connections
    are opened lazily when we execute queries.
    
    Args:
        config: Dict with POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB,
                POSTGRES_USER, POSTGRES_PASSWORD
    
    Returns:
        SQLAlchemy Engine instance
    
    Raises:
        Exception: If connection cannot be established
    """
    connection_string = (
        f"postgresql://{config['POSTGRES_USER']}:{config['POSTGRES_PASSWORD']}"
        f"@{config['POSTGRES_HOST']}:{config['POSTGRES_PORT']}/{config['POSTGRES_DB']}"
    )
    
    logger.info(
        f"Connecting to database: "
        f"{config['POSTGRES_USER']}@{config['POSTGRES_HOST']}:{config['POSTGRES_PORT']}/{config['POSTGRES_DB']}"
    )
    
    # Create engine with connection pooling
    engine = create_engine(connection_string)
    
    # Test the connection immediately
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise
    
    return engine


def load_to_raw(df: pd.DataFrame, engine: Engine) -> None:
    """
    Load DataFrame to raw.sales_raw table using a transaction.
    
    Strategy: DELETE existing data, then INSERT new data, all within a 
    single transaction. If anything fails, Postgres rolls back automatically.
    This ensures atomicity (all-or-nothing) and prevents queries from seeing
    an empty table during the load.
    
    The table is created if it doesn't exist. All columns are VARCHAR to
    preserve source data exactly as it appears in the CSV.
    
    Args:
        df: DataFrame to load (all columns should be strings)
        engine: SQLAlchemy engine
    
    Raises:
        Exception: If load fails (transaction will be rolled back)
    """
    logger.info("Starting load to raw.sales_raw")
    
    # Filter to only the expected columns (ignore any extra columns)
    df_to_load = df[EXPECTED_COLUMNS].copy()
    
    # Open a connection and start a transaction
    with engine.begin() as conn:
        # Create raw schema if it doesn't exist
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS raw"))
        logger.info("Ensured raw schema exists")
        
        # Create table if it doesn't exist (all VARCHAR columns)
        # We don't define a primary key or constraints here - this is a landing zone
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS raw.sales_raw (
            date VARCHAR,
            "store ID" VARCHAR,
            "PRODUCT_NAME" VARCHAR,
            " quantity" VARCHAR,
            "Price" VARCHAR,
            customer_type VARCHAR,
            "Payment Method" VARCHAR,
            "Transaction_ID" VARCHAR,
            " discount%" VARCHAR,
            region VARCHAR
        )
        """
        conn.execute(text(create_table_sql))
        logger.info("Ensured raw.sales_raw table exists")
        
        # Delete existing data (within the transaction)
        conn.execute(text("DELETE FROM raw.sales_raw"))
        logger.info("Deleted existing data from raw.sales_raw")
        
        # Insert new data using pandas to_sql
        # if_exists='append' because we just deleted the data
        # index=False means don't write the DataFrame index as a column
        # method='multi' is faster for bulk inserts
        df_to_load.to_sql(
            name='sales_raw',
            schema='raw',
            con=conn,
            if_exists='append',
            index=False,
            method='multi'
        )
        logger.info(f"Inserted {len(df_to_load)} rows into raw.sales_raw")
    
    # If we get here, the transaction committed successfully
    logger.info("Load completed successfully (transaction committed)")


def verify_load(engine: Engine, expected_rows: int) -> None:
    """
    Verify that the load succeeded by checking row count.
    
    This is a basic sanity check. More sophisticated verification would
    include checksums, sampling, or comparing row counts by key dimensions.
    
    Args:
        engine: SQLAlchemy engine
        expected_rows: Number of rows we expect to find in raw.sales_raw
    
    Raises:
        ValueError: If row count doesn't match expected
    """
    logger.info(f"Verifying load (expecting {expected_rows} rows)")
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM raw.sales_raw"))
        actual_rows = result.scalar()
    
    if actual_rows != expected_rows:
        raise ValueError(
            f"Row count mismatch: expected {expected_rows}, found {actual_rows}"
        )
    
    logger.info(f"Verification passed: {actual_rows} rows in raw.sales_raw")


def main():
    """
    Main execution flow with CLI argument parsing and error handling.
    
    Exit codes:
        0: Success
        1: Failure (any exception)
    """
    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description='Load sales CSV data into Postgres raw schema'
    )
    parser.add_argument(
        '--csv-path',
        required=True,
        help='Path to the sales CSV file'
    )
    args = parser.parse_args()
    
    try:
        # Step 1: Load configuration
        config = load_config()
        
        # Step 2: Read and validate CSV
        df = read_csv(args.csv_path)
        validate_structure(df)
        
        # Step 3: Connect to database
        engine = connect_db(config)
        
        # Step 4: Load data (within transaction)
        load_to_raw(df, engine)
        
        # Step 5: Verify load succeeded
        verify_load(engine, expected_rows=len(df))
        
        logger.info("Pipeline completed successfully")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()