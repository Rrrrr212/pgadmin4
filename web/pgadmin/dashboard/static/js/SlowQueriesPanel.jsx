/////////////////////////////////////////////////////////////
//
// pgAdmin 4 - PostgreSQL Tools
//
// Copyright (C) 2013 - 2026, The pgAdmin Development Team
// This software is released under the PostgreSQL Licence
//
//////////////////////////////////////////////////////////////
import { useState, useEffect } from 'react';
import { styled } from '@mui/material/styles';
import PropTypes from 'prop-types';
import { Box, Grid } from '@mui/material';
import * as echarts from 'echarts';
import ReactECharts from 'echarts-for-react';
import gettext from 'sources/gettext';
import getApiInstance from 'sources/api_instance';
import url_for from 'sources/url_for';
import SectionContainer from './components/SectionContainer';
import PgTable from 'sources/components/PgTable';
import { useTheme } from '@mui/material';
import EmptyPanelMessage from '../../../static/js/components/EmptyPanelMessage';
import RefreshButton from './components/RefreshButtons';

const Container = styled(Box)(({ theme }) => ({
  height: '100%',
  '& .SlowQueriesPanel-chartContainer': {
    height: '350px',
    padding: '0.5rem',
    backgroundColor: theme.palette.background.paper,
  },
  '& .SlowQueriesPanel-tableContainer': {
    maxHeight: '400px',
    overflow: 'auto',
    marginTop: '0.5rem',
  },
}));

function formatTime(ms) {
  if (ms >= 1000) {
    return (ms / 1000).toFixed(2) + 's';
  }
  return ms.toFixed(2) + 'ms';
}

function shortenQuery(query, maxLen = 100) {
  if (!query) return '';
  const trimmed = query.trim();
  if (trimmed.length <= maxLen) return trimmed;
  return trimmed.substring(0, maxLen) + '...';
}

export default function SlowQueriesPanel({ sid, did }) {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [refreshToggle, setRefreshToggle] = useState(false);
  const theme = useTheme();

  const fetchData = () => {
    setLoading(true);
    setError(null);

    let url = url_for('dashboard.slow_queries');
    url += '/' + sid;
    if (did && did > 0) {
      url += '/' + did;
    }

    const api = getApiInstance();
    api({
      url: url,
      type: 'GET',
    })
      .then((res) => {
        setData(res.data || []);
        setLoading(false);
      })
      .catch((err) => {
        let errMsg = gettext('Failed to retrieve slow queries data.');
        if (err.response?.data?.errormsg) {
          errMsg = err.response.data.errormsg;
        } else if (err.message) {
          errMsg = err.message;
        }
        setError(errMsg);
        setData([]);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
  }, [sid, did, refreshToggle]);

  const handleRefresh = () => {
    setRefreshToggle(!refreshToggle);
  };

  const getChartOption = () => {
    if (!data || data.length === 0) {
      return {
        title: {
          text: gettext('No data available'),
          left: 'center',
          textStyle: {
            color: theme.palette.text.secondary,
          },
        },
      };
    }

    const sortedData = [...data].sort((a, b) => b.mean_time - a.mean_time);
    const labels = sortedData.map((_item, idx) => {
      return gettext('Query') + ' ' + (idx + 1);
    });
    const values = sortedData.map((item) => parseFloat(item.mean_time));

    const isDark = theme.palette.mode === 'dark';
    const textColor = isDark ? '#cccccc' : '#333333';
    const axisColor = isDark ? '#555555' : '#cccccc';

    return {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'shadow',
        },
        formatter: (params) => {
          const item = sortedData[params[0].dataIndex];
          return `
            <div><strong>${gettext('Mean Time')}: ${formatTime(item.mean_time)}</strong></div>
            <div>${gettext('Calls')}: ${item.calls}</div>
            <div>${gettext('Total Time')}: ${formatTime(item.total_time)}</div>
            <div>${gettext('Max Time')}: ${formatTime(item.max_time)}</div>
          `;
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: labels,
        axisTick: {
          alignWithLabel: true,
        },
        axisLine: {
          lineStyle: {
            color: axisColor,
          },
        },
        axisLabel: {
          color: textColor,
        },
      },
      yAxis: {
        type: 'value',
        name: gettext('Mean Time (ms)'),
        nameTextStyle: {
          color: textColor,
        },
        axisLine: {
          lineStyle: {
            color: axisColor,
          },
        },
        axisLabel: {
          color: textColor,
          formatter: (value) => value.toFixed(0),
        },
      },
      series: [
        {
          name: gettext('Mean Time'),
          type: 'bar',
          data: values,
          barWidth: '60%',
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: '#83bff6' },
              { offset: 0.5, color: '#188df0' },
              { offset: 1, color: '#188df0' },
            ]),
          },
        },
      ],
    };
  };

  const columns = [
    {
      accessorKey: 'rank',
      header: '#',
      enableSorting: false,
      size: 40,
      minSize: 40,
    },
    {
      accessorKey: 'query',
      header: gettext('Query'),
      enableSorting: false,
      minSize: 200,
      cell: ({ row }) => {
        const query = row.original.query;
        return shortenQuery(query, 120);
      },
    },
    {
      accessorKey: 'calls',
      header: gettext('Calls'),
      enableSorting: true,
      size: 80,
      minSize: 80,
    },
    {
      accessorKey: 'total_time',
      header: gettext('Total Time'),
      enableSorting: true,
      size: 100,
      minSize: 100,
      cell: ({ cell }) => formatTime(cell.getValue()),
    },
    {
      accessorKey: 'mean_time',
      header: gettext('Mean Time'),
      enableSorting: true,
      size: 100,
      minSize: 100,
      cell: ({ cell }) => formatTime(cell.getValue()),
    },
    {
      accessorKey: 'max_time',
      header: gettext('Max Time'),
      enableSorting: true,
      size: 100,
      minSize: 100,
      cell: ({ cell }) => formatTime(cell.getValue()),
    },
    {
      accessorKey: 'rows',
      header: gettext('Rows'),
      enableSorting: true,
      size: 80,
      minSize: 80,
    },
  ];

  const tableData = data.map((row, idx) => ({
    ...row,
    rank: idx + 1,
  }));

  const titleExtras = (
    <RefreshButton onClick={handleRefresh} noBorder={false} />
  );

  return (
    <SectionContainer title={gettext('Slow Queries Analysis')} titleExtras={titleExtras} resizable defaultHeight={600}>
      <Container>
        {error && !loading && (
          <Box p={2}>
            <EmptyPanelMessage text={error} />
          </Box>
        )}
        {!error && (
          <Grid container spacing={2}>
            <Grid item xs={12}>
              <Box className="SlowQueriesPanel-chartContainer">
                <ReactECharts
                  option={getChartOption()}
                  style={{ height: '100%', width: '100%' }}
                  theme={theme.palette.mode === 'dark' ? 'dark' : undefined}
                />
              </Box>
            </Grid>
            <Grid item xs={12}>
              <Box className="SlowQueriesPanel-tableContainer">
                <PgTable
                  caveTable={false}
                  tableNoBorder={false}
                  columns={columns}
                  data={tableData}
                />
              </Box>
            </Grid>
          </Grid>
        )}
      </Container>
    </SectionContainer>
  );
}

SlowQueriesPanel.propTypes = {
  sid: PropTypes.number.isRequired,
  did: PropTypes.number.isRequired,
};
