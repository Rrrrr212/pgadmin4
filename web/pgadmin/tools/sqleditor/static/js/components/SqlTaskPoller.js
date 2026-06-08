/////////////////////////////////////////////////////////////
//
// pgAdmin 4 - PostgreSQL Tools
//
// Copyright (C) 2013 - 2026, The pgAdmin Development Team
// This software is released under the PostgreSQL Licence
//
//////////////////////////////////////////////////////////////
import url_for from 'sources/url_for';

export class SqlTaskPoller {
  constructor(api, transId) {
    this.api = api;
    this.transId = transId;
    this.taskId = null;
    this.startTime = null;
    this.pollingInterval = null;
    this.maxPollingTime = 300000;
  }

  setStartTime(time) {
    this.startTime = time;
  }

  getPollingDelay() {
    if (!this.startTime) return 1000;
    const seconds = parseInt((Date.now() - this.startTime.getTime()) / 1000);
    if (seconds >= 10 && seconds < 30) {
      return 500;
    } else if (seconds >= 30 && seconds < 60) {
      return 1000;
    } else if (seconds >= 60 && seconds < 90) {
      return 2000;
    } else if (seconds >= 90) {
      return 5000;
    }
    return 1000;
  }

  async submitTask(sql, explainObject = null) {
    const payload = {
      sql: sql,
      explain_plan: explainObject,
    };

    const response = await this.api.post(
      url_for('sqleditor.execute_sql_async', { trans_id: this.transId }),
      JSON.stringify(payload)
    );

    if (response.data && response.data.task_id) {
      this.taskId = response.data.task_id;
      return response.data;
    }

    throw new Error('Failed to submit SQL task');
  }

  async getTaskStatus() {
    if (!this.taskId) {
      throw new Error('No task ID available');
    }

    const response = await this.api.get(
      url_for('sqleditor.get_task_status', { task_id: this.taskId })
    );

    return response.data;
  }

  async getTaskResult() {
    if (!this.taskId) {
      throw new Error('No task ID available');
    }

    const response = await this.api.get(
      url_for('sqleditor.get_task_result', { task_id: this.taskId })
    );

    return response.data;
  }

  pollForStatus(onStatusUpdate, onError) {
    return new Promise((resolve, reject) => {
      const checkStatus = async () => {
        try {
          const statusData = await this.getTaskStatus();
          
          if (onStatusUpdate) {
            onStatusUpdate(statusData);
          }

          if (statusData.status === 'Success' || statusData.status === 'Error' || 
              statusData.status === 'Cancel') {
            resolve(statusData);
            return;
          }

          if (statusData.status === 'Failed') {
            reject(new Error('Task failed'));
            return;
          }

          const delay = this.getPollingDelay();
          this.pollingInterval = setTimeout(checkStatus, delay);
        } catch (error) {
          if (onError) {
            onError(error);
          }
          reject(error);
        }
      };

      checkStatus();
    });
  }

  async pollForResult(onResultsAvailable, onExplain, onPollError, explainObject, flags) {
    try {
      const statusData = await this.getTaskStatus();

      if (statusData.status === 'Busy' || statusData.status === 'Queued' || 
          statusData.status === 'Started') {
        const delay = this.getPollingDelay();
        this.pollingInterval = setTimeout(
          () => this.pollForResult(onResultsAvailable, onExplain, onPollError, explainObject, flags),
          delay
        );
        return;
      }

      if (statusData.status === 'Success' || statusData.status === 'finished') {
        const resultData = await this.getTaskResult();
        
        if (onResultsAvailable) {
          onResultsAvailable(resultData);
        }
        return;
      }

      if (statusData.status === 'Error' || statusData.status === 'failed') {
        const resultData = await this.getTaskResult();
        
        if (onPollError) {
          onPollError(resultData);
        }
        return;
      }

      if (statusData.status === 'Cancel') {
        const resultData = await this.getTaskResult();
        
        if (onPollError) {
          onPollError(resultData);
        }
        return;
      }

    } catch (error) {
      if (onPollError) {
        onPollError(error);
      }
    }
  }

  cancelPolling() {
    if (this.pollingInterval) {
      clearTimeout(this.pollingInterval);
      this.pollingInterval = null;
    }
  }

  reset() {
    this.cancelPolling();
    this.taskId = null;
    this.startTime = null;
  }
}

export default SqlTaskPoller;
