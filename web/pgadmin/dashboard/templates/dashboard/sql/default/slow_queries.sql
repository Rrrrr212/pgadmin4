/*pga4dash*/
SELECT
    userid,
    dbid,
    query,
    calls,
    ROUND(total_exec_time::numeric, 2) AS total_exec_time,
    ROUND(mean_exec_time::numeric, 2) AS mean_exec_time,
    ROUND(min_exec_time::numeric, 2) AS min_exec_time,
    ROUND(max_exec_time::numeric, 2) AS max_exec_time,
    ROUND(stddev_exec_time::numeric, 2) AS stddev_exec_time,
    rows,
    ROUND((shared_blks_hit + shared_blks_read)::numeric, 2) AS shared_blks_total,
    ROUND(shared_blks_hit::numeric, 2) AS shared_blks_hit,
    ROUND(shared_blks_read::numeric, 2) AS shared_blks_read
FROM
    pg_catalog.pg_stat_statements
{% if did %}WHERE
    dbid = {{ did }}{% endif %}
ORDER BY
    total_exec_time DESC
LIMIT 10
