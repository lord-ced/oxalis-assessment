"""
Unit tests for the ETL loader.

These are unit tests, not integration tests. We test individual functions
with mock data, not the full pipeline against a real database.

Integration tests (actual DB load) will come later in Phase 6.
"""

import pytest
import pandas as pd
import os
from unittest.mock import patch, MagicMock

# Import functions from our load module
from load import (
    validate_structure,
    load_config,
    read_csv,
    EXPECTED_COLUMNS
)


class TestValidateStructure:
    """Test suite for the validate_structure function."""
    
    def test_valid_structure(self):
        """Test that a properly structured DataFrame passes validation."""
        # Create a DataFrame with all expected columns
        data = {col: ['value1', 'value2'] for col in EXPECTED_COLUMNS}
        df = pd.DataFrame(data)
        
        # Should not raise any exception
        validate_structure(df)
    
    def test_empty_dataframe(self):
        """Test that an empty DataFrame raises ValueError."""
        # Create DataFrame with correct columns but no rows
        df = pd.DataFrame(columns=EXPECTED_COLUMNS)
        
        with pytest.raises(ValueError, match="CSV file is empty"):
            validate_structure(df)
    
    def test_missing_columns(self):
        """Test that missing required columns raises ValueError."""
        # Create DataFrame missing some columns
        data = {
            'transaction_id': ['T001'],
            'date': ['2024-01-01'],
            'store_id': ['S001']
            # Missing other required columns
        }
        df = pd.DataFrame(data)
        
        with pytest.raises(ValueError, match="missing required columns"):
            validate_structure(df)
    
    def test_extra_columns_warning(self, caplog):
        """Test that extra columns generate a warning but don't fail."""
        # Create DataFrame with all expected columns plus extra ones
        data = {col: ['value1', 'value2'] for col in EXPECTED_COLUMNS}
        data['extra_column_1'] = ['extra1', 'extra2']
        data['extra_column_2'] = ['extra3', 'extra4']
        df = pd.DataFrame(data)
        
        # Should not raise exception
        validate_structure(df)
        
        # Should log a warning about extra columns
        assert 'unexpected columns' in caplog.text.lower()


class TestLoadConfig:
    """Test suite for the load_config function."""
    
    def test_all_env_vars_present(self):
        """Test that config loads successfully when all env vars are set."""
        env_vars = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'testdb',
            'POSTGRES_USER': 'testuser',
            'POSTGRES_PASSWORD': 'testpass'
        }
        
        with patch.dict(os.environ, env_vars):
            config = load_config()
            
            assert config['POSTGRES_HOST'] == 'localhost'
            assert config['POSTGRES_PORT'] == '5432'
            assert config['POSTGRES_DB'] == 'testdb'
            assert config['POSTGRES_USER'] == 'testuser'
            assert config['POSTGRES_PASSWORD'] == 'testpass'
    
    def test_missing_env_vars(self):
        """Test that missing env vars raise ValueError listing all missing vars."""
        # Set only some of the required vars
        env_vars = {
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432'
            # Missing: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            with pytest.raises(ValueError, match="Missing required environment variables"):
                load_config()


class TestReadCSV:
    """Test suite for the read_csv function."""
    
    def test_read_csv_success(self, tmp_path):
        """Test reading a valid CSV file."""
        # Create a temporary CSV file
        csv_file = tmp_path / "test_sales.csv"
        csv_content = """transaction_id,date,store_id,region,product_category,quantity_sold,unit_price,discount,customer_type,payment_method
T001,2024-01-01,S001,North,Electronics,2,100.00,10%,Regular,Credit Card
T002,2024-01-02,S002,South,Clothing,1,50.00,5%,VIP,Cash"""
        
        csv_file.write_text(csv_content)
        
        # Read the CSV
        df = read_csv(str(csv_file))
        
        # Verify it was read correctly
        assert len(df) == 2
        assert list(df.columns) == EXPECTED_COLUMNS
        
        # Verify all columns are strings
        for col in df.columns:
            assert df[col].dtype == 'object'  # pandas uses 'object' for strings
    
    def test_read_csv_file_not_found(self):
        """Test that reading a non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            read_csv('/nonexistent/path/to/file.csv')
    
    def test_read_csv_preserves_string_values(self, tmp_path):
        """Test that numeric-looking values are preserved as strings."""
        csv_file = tmp_path / "test_values.csv"
        csv_content = """transaction_id,date,store_id,region,product_category,quantity_sold,unit_price,discount,customer_type,payment_method
T001,2024-01-01,S001,North,Electronics,002,100.00,10%,Regular,Credit Card"""
        
        csv_file.write_text(csv_content)
        
        df = read_csv(str(csv_file))
        
        # Verify that leading zeros are preserved (would be lost if parsed as int)
        assert df['quantity_sold'].iloc[0] == '002'
        
        # Verify that discount is preserved with % symbol
        assert df['discount'].iloc[0] == '10%'


class TestDatabaseFunctions:
    """
    Test suite for database connection and load functions.
    
    These are basic callable tests only. Full integration tests with a real
    database will be done in Phase 6.
    """
    
    def test_connect_db_function_exists(self):
        """Test that connect_db function is importable and callable."""
        from load import connect_db
        assert callable(connect_db)
    
    def test_load_to_raw_function_exists(self):
        """Test that load_to_raw function is importable and callable."""
        from load import load_to_raw
        assert callable(load_to_raw)
    
    def test_verify_load_function_exists(self):
        """Test that verify_load function is importable and callable."""
        from load import verify_load
        assert callable(verify_load)


# Test fixtures can be added here if needed in the future
@pytest.fixture
def sample_dataframe():
    """Fixture that provides a valid sample DataFrame for testing."""
    data = {col: ['value1', 'value2', 'value3'] for col in EXPECTED_COLUMNS}
    return pd.DataFrame(data)