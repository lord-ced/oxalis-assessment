{% macro log_dbt_run(stage, status) %}
  {%- set run_id = invocation_id -%}
  
  {%- if status == 'started' -%}
    {% set query %}
      INSERT INTO meta.pipeline_runs (run_id, stage, status, started_at)
      VALUES ('{{ run_id }}', '{{ stage }}', 'started', CURRENT_TIMESTAMP)
    {% endset %}
    
    {% do run_query(query) %}
    {% do log("Logged run start: " ~ run_id, info=true) %}
    
  {%- elif status == 'success' or status == 'failed' -%}
    {% set query %}
      UPDATE meta.pipeline_runs
      SET status = '{{ status }}',
          completed_at = CURRENT_TIMESTAMP,
          duration_seconds = EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at))
      WHERE run_id = '{{ run_id }}'
    {% endset %}
    
    {% do run_query(query) %}
    {% do log("Logged run end: " ~ status, info=true) %}
  {%- endif -%}
{% endmacro %}
