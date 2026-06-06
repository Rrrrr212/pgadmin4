/////////////////////////////////////////////////////////////
//
// pgAdmin 4 - PostgreSQL Tools
//
// Copyright (C) 2013 - 2026, The pgAdmin Development Team
// This software is released under the PostgreSQL Licence
//
//////////////////////////////////////////////////////////////
import { useState, useCallback, useRef, useEffect } from 'react';
import getApiInstance from '../../../../static/js/api_instance';
import url_for from 'sources/url_for';
import gettext from 'sources/gettext';

const POLL_INTERVAL = 1000; // 1 second
const MAX_POLL_DURATION = 300000; // 5 minutes

export const TASK_STATUS = {
  QUEUED: 'queued',
  STARTED: 'started',
  FINISHED: 'finished',
  FAILED: 'failed',
  NOT_FOUND: 'not_found'
};

export function useAsyncTaskPolling() {
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [isPolling, setIsPolling] = useState(false);
  const pollStartTimeRef = useRef(null);
  const pollIntervalRef = useRef(null);
  const apiRef = useRef(getApiInstance());

  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setIsPolling(false);
  }, []);

  const fetchTaskStatus = useCallback(async () => {
    if (!taskId) return;

    try {
      const url = url_for('sqleditor.task_status', {
        task_id: taskId
      });
      const response = await apiRef.current.get(url);
      const taskStatus = response.data.data;

      setStatus(taskStatus);

      if (taskStatus.status === 'finished' || taskStatus.status === 'failed') {
        // Task is done, fetch the result
        await fetchTaskResult();
        stopPolling();
      }

      // Check if we've exceeded max poll duration
      if (pollStartTimeRef.current) {
        const elapsed = Date.now() - pollStartTimeRef.current;
        if (elapsed > MAX_POLL_DURATION) {
          setError(gettext('Polling timed out - task taking too long'));
          stopPolling();
        }
      }
    } catch (err) {
      console.error('Error fetching task status:', err);
      setError(err.response?.data?.errormsg || gettext('Failed to check task status'));
      stopPolling();
    }
  }, [taskId, stopPolling]);

  const fetchTaskResult = useCallback(async () => {
    if (!taskId) return;

    try {
      const url = url_for('sqleditor.task_result', {
        task_id: taskId
      });
      const response = await apiRef.current.get(url);
      setResult(response.data.data);
    } catch (err) {
      console.error('Error fetching task result:', err);
      if (err.response?.status !== 202) {
        setError(err.response?.data?.errormsg || gettext('Failed to fetch task result'));
      }
    }
  }, [taskId]);

  const executeAsyncSQL = useCallback(async (transId, sql, connect = false) => {
    // Reset state
    setTaskId(null);
    setStatus(null);
    setResult(null);
    setError(null);

    try {
      const url = url_for('sqleditor.execute_sql_async', {
        trans_id: transId
      });

      const data = { sql: sql };
      if (connect) {
        data.connect = '1';
      }

      const response = await apiRef.current.post(url, data);

      if (response.data.success === 1) {
        const newTaskId = response.data.data.task_id;
        setTaskId(newTaskId);
        setStatus(response.data.data);
        setIsPolling(true);
        pollStartTimeRef.current = Date.now();

        // Start polling
        pollIntervalRef.current = setInterval(fetchTaskStatus, POLL_INTERVAL);

        return { success: true, taskId: newTaskId };
      } else {
        setError(response.data.errormsg || gettext('Failed to execute SQL query'));
        return { success: false, error: response.data.errormsg };
      }
    } catch (err) {
      console.error('Error executing async SQL:', err);
      const errorMsg = err.response?.data?.errormsg || gettext('Failed to start SQL execution');
      setError(errorMsg);
      return { success: false, error: errorMsg };
    }
  }, [fetchTaskStatus]);

  const cancelPolling = useCallback(() => {
    stopPolling();
  }, [stopPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    executeAsyncSQL,
    cancelPolling,
    taskId,
    status,
    result,
    error,
    isPolling
  };
}