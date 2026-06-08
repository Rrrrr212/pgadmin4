##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2026, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

"""RQ task module for asynchronous SQL execution."""

import pickle
import redis
from rq import Queue, get_current_job
from config import REDIS_URL, SQL_TASK_RESULT_TTL, SQL_TASK_TIMEOUT

redis_conn = redis.from_url(REDIS_URL)
sql_queue = Queue(name='sqleditor_sql_execution', connection=redis_conn)


def execute_sql_task(sql, trans_id, session_data, connection_params):
    """
    RQ task function that executes SQL asynchronously.
    
    Args:
        sql: SQL statement to execute
        trans_id: Transaction ID
        session_data: Pickled session data
        connection_params: Connection parameters dict
    
    Returns:
        dict: Execution result with status and data
    """
    from pgadmin.utils.driver import get_driver
    from config import PG_DEFAULT_DRIVER
    from pgadmin.tools.sqleditor.utils.constant_definition import ASYNC_OK, ASYNC_EXECUTION_ABORTED
    
    job = get_current_job()
    
    try:
        manager = get_driver(PG_DEFAULT_DRIVER).connection_manager(
            connection_params['sid']
        )
        conn = manager.connection(
            did=connection_params['did'],
            conn_id=connection_params['conn_id'],
            auto_reconnect=False,
            use_binary_placeholder=True,
            array_to_string=True,
            **({"database": connection_params.get('dbname')} if connection_params.get('dbname') else {})
        )
        
        if not conn.connected():
            return {
                'status': 'Error',
                'result': 'Connection to the server has been lost.',
                'error_info': 'CONNECTION_LOST'
            }
        
        status, result = conn.execute_async(
            sql,
            server_cursor=connection_params.get('server_cursor', False)
        )
        
        if not status:
            return {
                'status': 'Error',
                'result': result,
                'error_info': 'EXECUTION_FAILED'
            }
        
        status, result = conn.poll(formatted_exception_msg=True, no_result=True)
        
        if not status:
            if not conn.connected():
                return {
                    'status': 'Error',
                    'result': 'Connection to the server has been lost.',
                    'error_info': 'CONNECTION_LOST'
                }
            return {
                'status': 'Error',
                'result': result,
                'error_info': 'POLL_FAILED'
            }
        
        if status == ASYNC_OK:
            rows_affected = conn.rows_affected()
            st, result_data = conn.async_fetchmany_2darray(1001)
            
            messages = conn.messages()
            additional_messages = ''.join(messages) if messages else None
            notifies = conn.get_notifies()
            
            columns_info = conn.get_column_info()
            
            return {
                'status': 'Success',
                'result': result_data,
                'rows_affected': rows_affected,
                'additional_messages': additional_messages,
                'notifies': notifies,
                'colinfo': columns_info,
                'transaction_status': conn.transaction_status()
            }
        elif status == ASYNC_EXECUTION_ABORTED:
            return {
                'status': 'Cancel',
                'result': 'Query execution was cancelled.',
                'error_info': 'EXECUTION_ABORTED'
            }
        else:
            return {
                'status': 'Busy',
                'result': conn.messages(),
                'error_info': 'STILL_EXECUTING'
            }
            
    except Exception as e:
        return {
            'status': 'Error',
            'result': str(e),
            'error_info': 'EXCEPTION'
        }


def submit_sql_task(sql, trans_id, session_data, connection_params):
    """
    Submit a SQL execution task to the RQ queue.
    
    Args:
        sql: SQL statement to execute
        trans_id: Transaction ID
        session_data: Pickled session data
        connection_params: Connection parameters dict
    
    Returns:
        str: Task ID
    """
    job = sql_queue.enqueue(
        execute_sql_task,
        sql=sql,
        trans_id=trans_id,
        session_data=session_data,
        connection_params=connection_params,
        job_timeout=SQL_TASK_TIMEOUT,
        result_ttl=SQL_TASK_RESULT_TTL
    )
    return job.id


def get_task_status(task_id):
    """
    Get the status of a task.
    
    Args:
        task_id: Task ID
    
    Returns:
        str: Task status (queued, started, finished, failed)
    """
    from rq.job import Job
    job = Job.fetch(task_id, connection=redis_conn)
    return job.get_status()


def get_task_result(task_id):
    """
    Get the result of a task.
    
    Args:
        task_id: Task ID
    
    Returns:
        dict: Task result or None
    """
    from rq.job import Job
    job = Job.fetch(task_id, connection=redis_conn)
    
    if job.is_finished:
        return job.result
    elif job.is_failed:
        return {
            'status': 'Error',
            'result': str(job.exc_info),
            'error_info': 'TASK_FAILED'
        }
    elif job.is_started:
        return {
            'status': 'Busy',
            'result': 'Query is still executing...',
            'error_info': 'STILL_EXECUTING'
        }
    else:
        return {
            'status': 'Queued',
            'result': 'Query is waiting to be executed...',
            'error_info': 'QUEUED'
        }
