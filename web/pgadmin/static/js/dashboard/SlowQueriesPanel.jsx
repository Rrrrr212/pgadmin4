import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Box } from '@mui/material';
import { styled } from '@mui/material/styles';
import gettext from 'sources/gettext';
import getApiInstance from 'sources/api_instance';
import url_for from 'sources/url_for';
import ReactECharts from 'echarts-for-react';
import EmptyPanelMessage from '../components/EmptyPanelMessage';
import PgTable from '../components/PgTable';

const Root = styled('div')(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  height: '100%',
  width: '100%',
  padding: '8px',
  '& .chart-container': {
    height: '400px',
    width: '100%',
    marginBottom: '16px',
    flexShrink: 0
  },
  '& .table-container': {
    flex: 1,
    minHeight: 0,
    overflow: 'auto'
  }
}));

export default function SlowQueriesPanel({ sid, did, isActive }) {
  const [data, setData] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');

  const fetchData = async () => {
    if (!isActive || !sid) return;

    try {
      const _url = did
        ? url_for('dashboard.get_slow_queries_by_database_id', { sid: sid, did: did })
        : url_for('dashboard.get_slow_queries_by_server_id', { sid: sid });

      const api = getApiInstance();
      const res = await api.get(_url);
      if (res.data) {
        setData(res.data);
        setErrorMsg('');
      }
    } catch (error) {
      console.error(error);
      setErrorMsg(gettext('Failed to fetch slow queries. pg_stat_statements might not be installed or accessible.'));
    }
  };

  useEffect(() => {
    fetchData();
  }, [sid, did, isActive]);

  if (errorMsg) {
    return <EmptyPanelMessage text={errorMsg} />;
  }

  if (!data) {
    return <EmptyPanelMessage text={gettext('Loading...')} />;
  }

  if (data.length === 0) {
    return <EmptyPanelMessage text={gettext('No slow queries data available.')} />;
  }

  const chartOption = {
    title: {
      text: gettext('TOP 10 Slow Queries by Execution Time'),
      left: 'center'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    legend: {
      bottom: 0
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: gettext('Time (ms)')
    },
    yAxis: {
      type: 'category',
      data: data.map((d, i) => `Q${i + 1}`),
      inverse: true
    },
    series: [
      {
        name: gettext('Total Exec Time'),
        type: 'bar',
        data: data.map(d => parseFloat(d.total_exec_time_ms || 0)),
        itemStyle: { color: '#5470c6' }
      },
      {
        name: gettext('Mean Exec Time'),
        type: 'bar',
        data: data.map(d => parseFloat(d.mean_exec_time_ms || 0)),
        itemStyle: { color: '#91cc75' }
      }
    ]
  };

  const columns = [
    {
      header: gettext('ID'),
      accessorFn: (row, index) => `Q${index + 1}`,
      size: 60,
      enableSorting: false
    },
    {
      header: gettext('Query'),
      accessorKey: 'query',
      size: 400,
      enableSorting: false
    },
    {
      header: gettext('Calls'),
      accessorKey: 'calls',
      size: 80,
      enableSorting: true
    },
    {
      header: gettext('Total Time (ms)'),
      accessorKey: 'total_exec_time_ms',
      size: 120,
      enableSorting: true
    },
    {
      header: gettext('Mean Time (ms)'),
      accessorKey: 'mean_exec_time_ms',
      size: 120,
      enableSorting: true
    },
    {
      header: gettext('Rows'),
      accessorKey: 'rows',
      size: 80,
      enableSorting: true
    }
  ];

  return (
    <Root>
      <Box className="chart-container">
        <ReactECharts option={chartOption} style={{ height: '100%', width: '100%' }} />
      </Box>
      <Box className="table-container">
        <PgTable
          caveTable={false}
          columns={columns}
          data={data}
        />
      </Box>
    </Root>
  );
}

SlowQueriesPanel.propTypes = {
  sid: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  did: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  isActive: PropTypes.bool
};
