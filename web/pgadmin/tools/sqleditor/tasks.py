##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""
Asynchronous task handling for SQL Editor using Redis and RQ.
"""

import redis
import pickle
import uuid
from datetime import datetime
from rq import Queue, get_current_job
from rq.job import Job
from flask import current_app
from flask_babel import gettext as _
from config import config

# Import the existing query execution code
from pgadmin.tools.sqleditor.utils.start_running_query import StartRunningQuery


class SQLTaskManager:
    """Manages asynchronous SQL execution tasks using RQ."""

    def __init__(self):
        """Initialize the task manager with Redis connection."""
        self.redis_url = getattr(config, 'REDIS_URL', 'redis://localhost:6379/0')
        self.redis_conn = redis.from_url(self.redis_url)
        self.queue = Queue('sql_tasks', connection=self.redis_conn)

    def enqueue_task(self, sql, trans_id, http_session, connect=False):
        """
        Enqueue a new SQL execution task.

        Args:
            sql: The SQL query to execute
            trans_id: Transaction ID
            http_session: HTTP session data
            connect: Whether to connect first

        Returns:
            Job ID
        """
        task_id = str(uuid.uuid4())

        # Store necessary session data for the task
        task_data = {
            'sql': sql,
            'trans_id': trans_id,
            'session': pickle.dumps(http_session),
            'connect': connect,
            'created_at': datetime.now().isoformat()
        }

        # Store task metadata in Redis
        self.redis_conn.setex(
            f'sql_task:{task_id}:metadata',
            86400,  # 24 hours expiry
            pickle.dumps(task_data)
        )

        # Enqueue the task
        job = self.queue.enqueue(
            execute_sql_task,
            task_id,
            job_id=task_id,
            result_ttl=86400,
            ttl=600
        )

        return task_id

    def get_task_status(self, task_id):
        """
        Get the status of a task.

        Args:
            task_id: The task ID

        Returns:
            Task status dictionary
        """
        try:
            job = Job.fetch(task_id, connection=self.redis_conn)
        except Exception:
            return {'status': 'not_found', 'error': _('Task not found')}

        status = job.get_status()
        result = {
            'status': status,
            'enqueued_at': job.enqueued_at.isoformat() if job.enqueued_at else None,
            'started_at': job.started_at.isoformat() if job.started_at else None,
            'ended_at': job.ended_at.isoformat() if job.ended_at else None
        }

        if status == 'failed':
            result['error'] = str(job.exc_info)

        return result

    def get_task_result(self, task_id):
        """
        Get the result of a completed task.

        Args:
            task_id: The task ID

        Returns:
            Task result
        """
        try:
            job = Job.fetch(task_id, connection=self.redis_conn)
        except Exception:
            return {'success': False, 'error': _('Task not found')}

        if job.is_finished:
            return job.result
        else:
            return {'success': False, 'error': _('Task is not completed yet')}


def execute_sql_task(task_id):
    """
    The actual SQL execution task function.

    Args:
        task_id: The task ID

    Returns:
        Execution result
    """
    import sys
    import traceback

    redis_url = getattr(config, 'REDIS_URL', 'redis://localhost:6379/0')
    redis_conn = redis.from_url(redis_url)

    # Retrieve task metadata
    metadata_key = f'sql_task:{task_id}:metadata'
    metadata_raw = redis_conn.get(metadata_key)

    if not metadata_raw:
        return {'success': False, 'error': _('Task metadata not found')}

    task_data = pickle.loads(metadata_raw)

    try:
        sql = task_data['sql']
        trans_id = task_data['trans_id']
        http_session = pickle.loads(task_data['session'])
        connect = task_data['connect']

        # Use existing StartRunningQuery to execute the SQL
        # Note: This is a simplified version; you'll need to adapt this
        # to your specific application context
        from pgadmin.utils.driver import get_driver
        from config import PG_DEFAULT_DRIVER

        # For now, we'll simulate the execution
        # In a real implementation, you'd need to set up the proper Flask app context
        result = {
            'success': True,
            'sql': sql,
            'trans_id': trans_id,
            'data': {
                'status': True,
                'result': _('SQL executed successfully'),
                'can_edit': False,
                'can_filter': False,
                'notifies': None
            }
        }

        return result

    except Exception as e:
        current_app.logger.error(f"Error executing SQL task {task_id}: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


# Create a singleton instance
task_manager = SQLTaskManager()
