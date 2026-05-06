"""
Structural transformations for the ETL pipeline.

This module handles STRUCTURAL cleaning only (column names, basic formatting).
Semantic transformations (data values, business logic) happen in dbt.

Boundary:
- Python/transform.py: Column name normalization, basic structure fixes
- dbt/staging: Data value transformations, type casting, business rules
"""

import pandas as pd
import logging

logger = logging.getLogger(__name__)


# Mapping from messy source column names to clean target column names
COLUMN_MAPPING = {
    'date': 'date',
    'store ID': 'store_id',
    'PRODUCT_NAME': 'product_category',
    ' quantity': 'quantity_sold',          # Note: leading space in source
    'Price': 'unit_price',
    'customer_type': 'customer_type',
    'Payment Method': 'payment_method',
    'Transaction_ID': 'transaction_id',
    ' discount%': 'discount',              # Note: leading space in source
    'region': 'region'
}


def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names from source to clean canonical names.
    
    This is structural cleaning only:
    - Rename columns to snake_case
    - Remove leading/trailing spaces from column names
    - Standardize to lowercase with underscores
    
    We do NOT clean data values here. That happens in dbt.
    
    Args:
        df: DataFrame with messy source column names
    
    Returns:
        DataFrame with clean column names, same data values
    
    Raises:
        ValueError: If source columns don't match expected mapping
    """
    logger.info("Cleaning column names (structural transformation)")
    
    # Verify all expected source columns are present
    source_columns = set(df.columns)
    expected_source = set(COLUMN_MAPPING.keys())
    
    missing = expected_source - source_columns
    if missing:
        raise ValueError(
            f"Source CSV missing expected columns: {', '.join(sorted(missing))}"
        )
    
    # Check for unexpected columns (warning only)
    extra = source_columns - expected_source
    if extra:
        logger.warning(
            f"Source CSV has unexpected columns (will be dropped): {', '.join(sorted(extra))}"
        )
    
    # Rename columns using the mapping
    df_clean = df.rename(columns=COLUMN_MAPPING)
    
    # Keep only the mapped columns (drop any extras)
    target_columns = list(COLUMN_MAPPING.values())
    df_clean = df_clean[target_columns]
    
    logger.info(f"Column names cleaned: {len(target_columns)} columns normalized")
    
    return df_clean