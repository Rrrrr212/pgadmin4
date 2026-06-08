import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Box } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import gettext from 'sources/gettext';
import url_for from 'sources/url_for';
import EmptyPanelMessage from 'sources/components/EmptyPanelMessage';
import PgTable from 'sources/components/PgTable';
import SectionContainer from '../../../dashboard/static/js/components/SectionContainer';
import getApiInstance from 'sources/api_instance';

export default function SlowQueriesPanel({ sid, did, serverConnected, dbConnected, pageVisible }) {
  const [data, setData] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!pageVisible || !serverConnected) {
      return;
    }

    if (did && !dbConnected) {
      return;
    }

    const fetchData = async () => {
      setLoading(true);
      setErrorMsg(null);
      let url = url_for('dashboard.slow_queries');
      if (did) {
        url += '/' + sid + '/' + did;
      } else {
        url += '/' + sid;
      }

      try {
        const api = getApiInstance();
        const response = await api.get(url);
        setData(response.data);
      } catch (error) {
        console.error(error);
        setErrorMsg(gettext('Failed to fetch slow queries data.'));
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [sid, did, pageVisible, serverConnected, dbConnected]);

  const getChartOption = () => {
    const queries = data.map((item, index) => `Query ${index + 1}`);
    const executionTimes = data.map(item => item.total_exec_time);

    return {
      title: {
        text: gettext('Top 10 Slow Queries by Execution Time'),
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow'
        },
        formatter: function (params) {
          const dataIndex = params[0].dataIndex;
          const row = data[dataIndex];
          let tooltip = `<b>Query ${dataIndex + 1}</b><br/>`;
          tooltip += `Execution Time: ${row.total_exec_time} ms<br/>`;
          tooltip += `Calls: ${row.calls}<br/>`;
          tooltip += `Rows: ${row.rows}<br/>`;
          return tooltip;
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'value',
        name: 'Execution Time (ms)',
        nameLocation: 'middle',
        nameGap: 30
      },
      yAxis: {
        type: 'category',
        data: queries.reverse(),
      },
      series: [
        {
          name: 'Execution Time',
          type: 'bar',
          data: executionTimes.reverse(),
          itemStyle: {
            color: '#5470c6'
          }
        }
      ]
    };
  };

  const columns = [
    {
      header: gettext('Query'),
      accessorKey: 'query',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
      size: 400,
      Cell: ({ cell }) => (
        <div style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={cell.getValue()}>
          {cell.getValue()}
        </div>
      ),
    },
    {
      header: gettext('Total Exec Time (ms)'),
      accessorKey: 'total_exec_time',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
    },
    {
      header: gettext('Calls'),
      accessorKey: 'calls',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
    },
    {
      header: gettext('Mean Time (ms)'),
      accessorKey: 'mean_exec_time',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
    },
    {
      header: gettext('Min Time (ms)'),
      accessorKey: 'min_exec_time',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
    },
    {
      header: gettext('Max Time (ms)'),
      accessorKey: 'max_exec_time',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
    },
    {
      header: gettext('Rows'),
      accessorKey: 'rows',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
    }
  ];

  if (!serverConnected || (did && !dbConnected)) {
    return (
      <div className="Dashboard-emptyPanel">
        <EmptyPanelMessage text={gettext('Please connect to the selected server/database to view slow queries.')} />
      </div>
    );
  }

  if (errorMsg) {
    return (
      <div className="Dashboard-emptyPanel">
        <EmptyPanelMessage text={errorMsg} />
      </div>
    );
  }

  if (!loading && data.length === 0) {
    return (
      <div className="Dashboard-emptyPanel">
        <EmptyPanelMessage text={gettext('No slow queries data available or pg_stat_statements is not enabled.')} />
      </div>
    );
  }

  return (
    <Box display="flex" flexDirection="column" height="100%">
      <Box flex={1} minHeight={300} mb={2}>
        <ReactECharts
          option={getChartOption()}
          style={{ height: '100%', width: '100%' }}
          notMerge={true}
          lazyUpdate={true}
        />
      </Box>
      <Box flex={1} minHeight={0}>
        <SectionContainer title={gettext('Slow Queries Details')}>
          <PgTable
            columns={columns}
            data={data}
            caveTable={false}
            tableNoBorder={false}
          />
        </SectionContainer>
      </Box>
    </Box>
  );
}

SlowQueriesPanel.propTypes = {
  sid: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  did: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  serverConnected: PropTypes.bool,
  dbConnected: PropTypes.bool,
  pageVisible: PropTypes.bool,
};
