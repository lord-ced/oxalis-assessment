"""
Metadata tracking for pipeline observability.

Logs each pipeline run to meta.pipeline_runs table for monitoring,
debugging, and historical analysis.
"""

import uuid
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.engine import Engine
import logging

logger = logging.getLogger(__name__)


class PipelineRunTracker:
    """
    Context manager for tracking pipeline run metadata.
    
    Usage:
        with PipelineRunTracker(engine, 'etl_load') as tracker:
            # do work
            tracker.set_rows_processed(51)
    """
    
    def __init__(self, engine: Engine, stage: str):
        self.engine = engine
        self.stage = stage
        self.run_id = str(uuid.uuid4())
        self.started_at = None
        self.rows_processed = None
        self.metadata = {}
    
    def __enter__(self):
        """Log run start."""
        self.started_at = datetime.now()
        
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO meta.pipeline_runs 
                        (run_id, stage, status, started_at)
                    VALUES 
                        (:run_id, :stage, 'started', :started_at)
                """), {
                    'run_id': self.run_id,
                    'stage': self.stage,
                    'started_at': self.started_at
                })
            logger.info(f"Pipeline run started: {self.run_id} ({self.stage})")
        except Exception as e:
            logger.warning(f"Failed to log run start: {e}")
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log run completion or failure."""
        completed_at = datetime.now()
        duration = (completed_at - self.started_at).total_seconds()
        
        if exc_type is None:
            # Success
            status = 'success'
            error_message = None
        else:
            # Failure
            status = 'failed'
            error_message = str(exc_val)
        
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    UPDATE meta.pipeline_runs
                    SET status = :status,
                        rows_processed = :rows_processed,
                        duration_seconds = :duration,
                        error_message = :error_message,
                        completed_at = :completed_at
                    WHERE run_id = :run_id
                """), {
                    'run_id': self.run_id,
                    'status': status,
                    'rows_processed': self.rows_processed,
                    'duration': duration,
                    'error_message': error_message,
                    'completed_at': completed_at,
                    'metadata': None  # Could serialize self.metadata to JSON
                })
            logger.info(
                f"Pipeline run {status}: {self.run_id} "
                f"({duration:.2f}s, {self.rows_processed or 0} rows)"
            )
        except Exception as e:
            logger.warning(f"Failed to log run completion: {e}")
        
        # Don't suppress the original exception
        return False
    
    def set_rows_processed(self, count: int):
        """Update row count during processing."""
        self.rows_processed = count
    
    def add_metadata(self, key: str, value):
        """Add stage-specific metadata."""
        self.metadata[key] = value
