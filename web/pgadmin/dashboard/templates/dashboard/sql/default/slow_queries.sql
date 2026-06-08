/*pga4dash*/
SELECT
  queryid,
  substring(query from 1 for 200) as query,
  calls,
  total_time / 1000 as total_time_sec,
  mean_time / 1000 as mean_time_sec,
  max_time / 1000 as max_time_sec,
  total_time / calls as avg_time,
  rows,
  shared_blks_hit,
  shared_blks_read,
  shared_blks_dirtied,
  shared_blks_written,
  local_blks_hit,
  local_blks_read,
  local_blks_dirtied,
  local_blks_written,
  temp_blks_read,
  temp_blks_written,
  blk_read_time,
  blk_write_time
FROM pg_stat_statements
{% if did %}
WHERE dbid = {{ did }}
{% endif %}
ORDER BY mean_time DESC
LIMIT 10
