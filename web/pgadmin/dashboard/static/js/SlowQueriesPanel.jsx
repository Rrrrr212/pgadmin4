/////////////////////////////////////////////////////////////
//
// pgAdmin 4 - PostgreSQL Tools
//
// Copyright (C) 2013 - 2026, The pgAdmin Development Team
// This software is released under the PostgreSQL Licence
//
//////////////////////////////////////////////////////////////

import { useState, useEffect } from 'react';
import PgTable from 'sources/components/PgTable';
import gettext from 'sources/gettext';
import PropTypes from 'prop-types';
import url_for from 'sources/url_for';
import getApiInstance from 'sources/api_instance';
import { Box, Tabs, Tab } from '@mui/material';
import { parseApiError } from '../../static/js/api_instance';
import SectionContainer from './components/SectionContainer';
import RefreshButton from './components/RefreshButtons';
import TabPanel from '../../static/js/components/TabPanel';
import ChartContainer from './components/ChartContainer';
import StreamingChart from '../../static/js/components/PgChart/StreamingChart';
import { DATA_POINT_SIZE } from 'sources/chartjs';
import { styled } from '@mui/material/styles';
import EmptyPanelMessage from '../../static/js/components/EmptyPanelMessage';

const StyledBox = styled(Box)(({ theme }) => ({
  height: '100%',
  width: '100%',
  display: 'flex',
  flexDirection: 'column',
}));

export default function SlowQueriesPanel({
  sid,
  did,
  serverConnected,
}) {
  const [slowQueries, setSlowQueries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refresh, setRefresh] = useState(false);
  const [activeTab, setActiveTab] = useState(0);

  const api = getApiInstance();

  const tableColumns = [
    {
      header: gettext('Query ID'),
      accessorKey: 'queryid',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
      minSize: 80,
      size: 80,
    },
    {
      header: gettext('Query'),
      accessorKey: 'query',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
      minSize: 200,
    },
    {
      header: gettext('Calls'),
      accessorKey: 'calls',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
      minSize: 60,
      size: 60,
    },
    {
      header: gettext('Total Time (s)'),
      accessorKey: 'total_time_sec',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
      minSize: 80,
      size: 80,
    },
    {
      header: gettext('Avg Time (ms)'),
      accessorKey: 'avg_time',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
      minSize: 80,
      size: 80,
    },
    {
      header: gettext('Max Time (s)'),
      accessorKey: 'max_time_sec',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
      minSize: 80,
      size: 80,
    },
    {
      header: gettext('Rows'),
      accessorKey: 'rows',
      enableSorting: true,
      enableResizing: true,
      enableFilters: true,
      minSize: 60,
      size: 60,
    },
  ];

  const fetchSlowQueries = () => {
    if (!sid || !serverConnected) {
      setLoading(false);
      return;
    }

    let url = url_for('dashboard.slow_queries');
    if (did) {
      url = url_for('dashboard.get_slow_queries_by_database_id', {
        sid: sid,
        did: did,
      });
    } else {
      url = url_for('dashboard.get_slow_queries_by_server_id', {
        sid: sid,
      });
    }

    api.get(url)
      .then((response) => {
        setSlowQueries(response.data || []);
        setError(null);
      })
      .catch((err) => {
        setError(
          parseApiError(err) || gettext('Failed to fetch slow queries')
        );
        setSlowQueries([]);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    setLoading(true);
    fetchSlowQueries();
  }, [sid, did, serverConnected, refresh]);

  const chartData = {
    datasets: [
      {
        label: gettext('Average Time (ms)'),
        data: slowQueries.map((q, i) => ({ x: i + 1, y: q.avg_time })),
        borderColor: '#1e88e5',
        backgroundColor: 'rgba(30, 136, 229, 0.2)',
      },
    ],
  };

  return (
    <StyledBox>
      {!serverConnected && (
        <div className="Dashboard-emptyPanel">
          <EmptyPanelMessage
            text={gettext('Please connect to the selected server to view slow queries')}
          />
        </div>
      )}

      {serverConnected && (
        <>
          <Box>
            <Tabs
              value={activeTab}
              onChange={(_, newValue) => setActiveTab(newValue)}
            >
              <Tab label={gettext('Queries')} />
              <Tab label={gettext('Chart')} />
            </Tabs>
          </Box>

          <TabPanel
            value={activeTab}
            index={0}
            classNameRoot="Dashboard-tabPanel"
          >
            <SectionContainer
              title={gettext('Top 10 Slow Queries')}
              titleExtras={
                <RefreshButton
                  onClick={() => setRefresh(!refresh)}
                  noBorder={false}
                />
              }
            >
              {loading && (
                <div className="Dashboard-emptyPanel">
                  <EmptyPanelMessage text={gettext('Loading...')} />
                </div>
              )}

              {!loading && error && (
                <div className="Dashboard-emptyPanel">
                  <EmptyPanelMessage text={error} />
                </div>
              )}

              {!loading && !error && (
                <PgTable
                  columns={tableColumns}
                  data={slowQueries}
                  caveTable={false}
                  tableNoBorder={false}
                />
              )}
            </SectionContainer>
          </TabPanel>

          <TabPanel
            value={activeTab}
            index={1}
            classNameRoot="Dashboard-tabPanel"
          >
            <SectionContainer
              title={gettext('Slow Query Analysis')}
              titleExtras={
                <RefreshButton
                  onClick={() => setRefresh(!refresh)}
                  noBorder={false}
                />
              }
            >
              {loading && (
                <div className="Dashboard-emptyPanel">
                  <EmptyPanelMessage text={gettext('Loading...')} />
                </div>
              )}

              {!loading && error && (
                <div className="Dashboard-emptyPanel">
                  <EmptyPanelMessage text={error} />
                </div>
              )}

              {!loading && !error && (
                <ChartContainer
                  id="slow-queries-chart"
                  title={gettext('Average Query Time')}
                  datasets={chartData.datasets}
                  errorMsg={null}
                  isTest={false}
                >
                  <StreamingChart
                    data={chartData}
                    dataPointSize={DATA_POINT_SIZE}
                    xRange={10}
                    options={{
                      showDataPoints: true,
                      showTooltip: true,
                      lineBorderWidth: 2,
                    }}
                  />
                </ChartContainer>
              )}
            </SectionContainer>
          </TabPanel>
        </>
      )}
    </StyledBox>
  );
}

SlowQueriesPanel.propTypes = {
  sid: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  did: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  serverConnected: PropTypes.bool,
};
