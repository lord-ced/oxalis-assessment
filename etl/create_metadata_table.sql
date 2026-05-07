-- Metadata tracking table for pipeline observability
-- Captures every run of ETL and dbt stages

CREATE SCHEMA IF NOT EXISTS meta;

CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
    run_id VARCHAR PRIMARY KEY,
    stage VARCHAR NOT NULL,  -- 'etl_load', 'dbt_run', 'dbt_test'
    status VARCHAR NOT NULL,  -- 'started', 'success', 'failed'
    rows_processed INTEGER,
    duration_seconds NUMERIC(10,2),
    error_message TEXT,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    metadata JSONB  -- Flexible field for stage-specific details
);

-- Index for querying recent runs
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_started_at 
    ON meta.pipeline_runs(started_at DESC);

-- Index for filtering by status
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status 
    ON meta.pipeline_runs(status);
