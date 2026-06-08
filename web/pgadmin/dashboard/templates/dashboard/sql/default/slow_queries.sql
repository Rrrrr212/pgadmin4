/*pga4dash*/
SELECT
    queryid,
    query,
    calls,
    total_time,
    mean_time,
    max_time,
    min_time,
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
FROM
    pg_catalog.pg_stat_statements
{% if did %}WHERE
    dbid = (SELECT oid FROM pg_catalog.pg_database WHERE datname = (SELECT datname FROM pg_catalog.pg_database WHERE oid = {{ did }})){% endif %}
ORDER BY
    mean_time DESC
LIMIT 10
