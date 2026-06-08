/////////////////////////////////////////////////////////////
//
// pgAdmin 4 - PostgreSQL Tools
//
// Copyright (C) 2013 - 2026, The pgAdmin Development Team
// This software is released under the PostgreSQL Licence
//
//////////////////////////////////////////////////////////////
import { useState, useEffect, useCallback, useMemo } from 'react';
import { styled } from '@mui/material/styles';
import gettext from 'sources/gettext';
import PropTypes from 'prop-types';
import url_for from 'sources/url_for';
import getApiInstance from 'sources/api_instance';
import ReactECharts from 'echarts-for-react';
import { Box, Grid } from '@mui/material';
import SectionContainer from './components/SectionContainer';
import EmptyPanelMessage from '../../../static/js/components/EmptyPanelMessage';
import RefreshButton from './components/RefreshButtons';

const Root = styled('div')(({theme}) => ({
  height: '100%',
  width: '100%',
  overflow: 'auto',
  padding: '4px',
  '& .SlowQueriesPanel-chartArea': {
    marginBottom: '8px',
  },
  '& .SlowQueriesPanel-queryCell': {
    maxWidth: '500px',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
    cursor: 'pointer',
  },
  '& .SlowQueriesPanel-queryFull': {
    maxWidth: '100%',
    overflow: 'auto',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-all',
  },
  '& .SlowQueriesPanel-detailTable': {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.8rem',
    '& th': {
      textAlign: 'left',
      padding: '6px 8px',
      borderBottom: '2px solid ' + theme.otherVars.borderColor,
      backgroundColor: theme.otherVars.tableBg,
      fontWeight: 'bold',
      position: 'sticky',
      top: 0,
      zIndex: 1,
    },
    '& td': {
      padding: '6px 8px',
      borderBottom: '1px solid ' + theme.otherVars.borderColor,
    },
    '& tr:hover td': {
      backgroundColor: theme.palette.action.hover,
    },
  },
}));

function truncateQuery(query, maxLen = 80) {
  if (!query) return '';
  query = query.replace(/\s+/g, ' ').trim();
  if (query.length > maxLen) {
    return query.substring(0, maxLen) + '...';
  }
  return query;
}

function formatMs(val) {
  if (val == null) return '-';
  return val + ' ms';
}

function formatCalls(val) {
  if (val == null) return '-';
  return val.toLocaleString();
}

export default function SlowQueriesPanel({sid, did, serverConnected}) {
  const [slowQueries, setSlowQueries] = useState([]);
  const [errorMsg, setErrorMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [refresh, setRefresh] = useState(false);
  const [expandedRow, setExpandedRow] = useState(null);

  const fetchSlowQueries = useCallback(() => {
    if (!sid || !serverConnected) return;

    setLoading(true);
    setErrorMsg('');

    let url = url_for('dashboard.slow_queries') + '/' + sid;
    if (did) {
      url += '/' + did;
    }

    const api = getApiInstance();
    api({
      url: url,
      type: 'GET',
    })
      .then((res) => {
        setSlowQueries(res.data || []);
        setLoading(false);
      })
      .catch((error) => {
        let msg = gettext('Failed to retrieve slow query data.');
        if (error?.response?.data?.errormsg) {
          msg = error.response.data.errormsg;
        }
        setErrorMsg(msg);
        setSlowQueries([]);
        setLoading(false);
      });
  }, [sid, did, serverConnected]);

  useEffect(() => {
    fetchSlowQueries();
  }, [fetchSlowQueries, refresh]);

  const barChartOption = useMemo(() => {
    if (!slowQueries || slowQueries.length === 0) return null;

    const labels = slowQueries.map((row, i) => {
      return '#' + (i + 1) + ' ' + truncateQuery(row.query, 40);
    });
    const totalExecTimes = slowQueries.map((row) => row.total_exec_time || 0);
    const meanExecTimes = slowQueries.map((row) => row.mean_exec_time || 0);

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function(params) {
          let tip = '';
          params.forEach(function(p) {
            tip += p.marker + ' ' + p.seriesName + ': ' + p.value + ' ms<br/>';
          });
          const idx = params[0].dataIndex;
          tip += '<br/>' + gettext('Full Query') + ':<br/>' + slowQueries[idx].query;
          return tip;
        },
      },
      legend: {
        data: [gettext('Total Exec Time'), gettext('Mean Exec Time')],
        top: 0,
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '40px',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: gettext('Time (ms)'),
        nameLocation: 'middle',
        nameGap: 30,
      },
      yAxis: {
        type: 'category',
        data: labels.reverse(),
        axisLabel: {
          width: 160,
          overflow: 'truncate',
          fontSize: 11,
        },
      },
      series: [
        {
          name: gettext('Total Exec Time'),
          type: 'bar',
          data: totalExecTimes.reverse(),
          itemStyle: {
            color: '#5470c6',
          },
        },
        {
          name: gettext('Mean Exec Time'),
          type: 'bar',
          data: meanExecTimes.reverse(),
          itemStyle: {
            color: '#91cc75',
          },
        },
      ],
    };
  }, [slowQueries]);

  const hitRateChartOption = useMemo(() => {
    if (!slowQueries || slowQueries.length === 0) return null;

    const labels = slowQueries.map((row, i) => {
      return '#' + (i + 1) + ' ' + truncateQuery(row.query, 40);
    });
    const hitRates = slowQueries.map((row) => {
      const total = parseFloat(row.shared_blks_total) || 0;
      const hit = parseFloat(row.shared_blks_hit) || 0;
      if (total === 0) return 100;
      return Math.round((hit / total) * 10000) / 100;
    });

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: function(params) {
          const p = params[0];
          return p.marker + ' ' + gettext('Cache Hit Rate') + ': ' + p.value + '%';
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10px',
        containLabel: true,
      },
      xAxis: {
        type: 'value',
        name: gettext('Hit Rate (%)'),
        max: 100,
        nameLocation: 'middle',
        nameGap: 30,
      },
      yAxis: {
        type: 'category',
        data: labels.reverse(),
        axisLabel: {
          width: 160,
          overflow: 'truncate',
          fontSize: 11,
        },
      },
      series: [
        {
          name: gettext('Cache Hit Rate'),
          type: 'bar',
          data: hitRates.reverse(),
          itemStyle: {
            color: function(params) {
              const val = params.value;
              if (val >= 99) return '#91cc75';
              if (val >= 90) return '#fac858';
              return '#ee6666';
            },
          },
        },
      ],
    };
  }, [slowQueries]);

  if (!sid || !serverConnected) {
    return (
      <Root>
        <EmptyPanelMessage text={gettext('Please connect to the selected server to view slow queries.')} />
      </Root>
    );
  }

  if (errorMsg) {
    return (
      <Root>
        <EmptyPanelMessage text={errorMsg} />
      </Root>
    );
  }

  if (loading && slowQueries.length === 0) {
    return (
      <Root>
        <EmptyPanelMessage text={gettext('Loading slow query data...')} />
      </Root>
    );
  }

  if (slowQueries.length === 0 && !loading) {
    return (
      <Root>
        <Box display="flex" justifyContent="flex-end" mb={1}>
          <RefreshButton noBorder={false} onClick={() => setRefresh(!refresh)} />
        </Box>
        <EmptyPanelMessage text={gettext('No slow query data available. Ensure pg_stat_statements extension is enabled.')} />
      </Root>
    );
  }

  return (
    <Root>
      <Box display="flex" justifyContent="flex-end" mb={1}>
        <RefreshButton noBorder={false} onClick={() => setRefresh(!refresh)} />
      </Box>

      <div className="SlowQueriesPanel-chartArea">
        <Grid container spacing={0.5}>
          <Grid size={{ md: 7 }}>
            <SectionContainer title={gettext('TOP 10 Slow Queries by Execution Time')}>
              {barChartOption && (
                <ReactECharts
                  option={barChartOption}
                  style={{ height: '360px', width: '100%' }}
                  notMerge={true}
                  lazyUpdate={true}
                />
              )}
            </SectionContainer>
          </Grid>
          <Grid size={{ md: 5 }}>
            <SectionContainer title={gettext('Cache Hit Rate (%)')}>
              {hitRateChartOption && (
                <ReactECharts
                  option={hitRateChartOption}
                  style={{ height: '360px', width: '100%' }}
                  notMerge={true}
                  lazyUpdate={true}
                />
              )}
            </SectionContainer>
          </Grid>
        </Grid>
      </div>

      <SectionContainer title={gettext('Slow Query Details')} resizable={true} defaultHeight={300}>
        <div style={{ overflow: 'auto', maxHeight: '400px' }}>
          <table className="SlowQueriesPanel-detailTable">
            <thead>
              <tr>
                <th>#</th>
                <th>{gettext('Query')}</th>
                <th>{gettext('Calls')}</th>
                <th>{gettext('Total Time')}</th>
                <th>{gettext('Mean Time')}</th>
                <th>{gettext('Min Time')}</th>
                <th>{gettext('Max Time')}</th>
                <th>{gettext('StdDev Time')}</th>
                <th>{gettext('Rows')}</th>
                <th>{gettext('Cache Hit Rate')}</th>
              </tr>
            </thead>
            <tbody>
              {slowQueries.map((row, i) => {
                const total = parseFloat(row.shared_blks_total) || 0;
                const hit = parseFloat(row.shared_blks_hit) || 0;
                const hitRate = total === 0 ? '100%' : Math.round((hit / total) * 10000) / 100 + '%';

                return (
                  <tr key={i}>
                    <td>{i + 1}</td>
                    <td>
                      {expandedRow === i ? (
                        <div
                          className="SlowQueriesPanel-queryFull"
                          onClick={() => setExpandedRow(null)}
                          title={gettext('Click to collapse')}
                        >
                          {row.query}
                        </div>
                      ) : (
                        <div
                          className="SlowQueriesPanel-queryCell"
                          onClick={() => setExpandedRow(i)}
                          title={gettext('Click to expand')}
                        >
                          {truncateQuery(row.query, 100)}
                        </div>
                      )}
                    </td>
                    <td>{formatCalls(row.calls)}</td>
                    <td>{formatMs(row.total_exec_time)}</td>
                    <td>{formatMs(row.mean_exec_time)}</td>
                    <td>{formatMs(row.min_exec_time)}</td>
                    <td>{formatMs(row.max_exec_time)}</td>
                    <td>{formatMs(row.stddev_exec_time)}</td>
                    <td>{row.rows != null ? row.rows.toLocaleString() : '-'}</td>
                    <td>{hitRate}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </SectionContainer>
    </Root>
  );
}

SlowQueriesPanel.propTypes = {
  sid: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  did: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  serverConnected: PropTypes.bool,
};
