SELECT query,
       calls,
       round(total_exec_time::numeric, 2) as total_exec_time_ms,
       round(mean_exec_time::numeric, 2) as mean_exec_time_ms,
       rows
FROM pg_stat_statements
{% if did %}
WHERE dbid = {{ did }}
{% endif %}
ORDER BY total_exec_time DESC
LIMIT 10;
