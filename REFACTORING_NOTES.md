# SQL Editor Async Task Queue Refactoring

## Overview

This refactoring converts the synchronous blocking SQL execution in pgAdmin4's SQL Editor to an asynchronous task queue pattern using Redis and RQ (Redis Queue).

## Architecture Changes

### Before (Synchronous/Threading-based)
- SQL execution used Python threading with `StartRunningQuery` class
- Frontend polled `/sqleditor/poll/<trans_id>` endpoint
- Connection state maintained in Flask session with pickle-serialized objects
- Long-running queries could block worker threads

### After (Redis + RQ Task Queue)
- SQL execution submitted as RQ tasks to Redis queue
- Dedicated RQ workers process SQL execution tasks
- Frontend polls task status and result via new endpoints
- Better scalability and resource management

## Files Modified/Created

### 1. Configuration (`web/config.py`)

Added Redis and RQ configuration settings:

```python
REDIS_URL = env('REDIS_URL') or 'redis://localhost:6379/0'
SQL_TASK_QUEUE_NAME = 'sqleditor_sql_execution'
SQL_TASK_RESULT_TTL = 3600  # seconds
SQL_TASK_TIMEOUT = 300  # seconds
```

### 2. Backend Task Module (`web/pgadmin/tools/sqleditor/utils/sql_task_queue.py`)

New module containing:
- `execute_sql_task()`: RQ task function that executes SQL asynchronously
- `submit_sql_task()`: Submits SQL execution to RQ queue
- `get_task_status()`: Retrieves task status from Redis
- `get_task_result()`: Retrieves task result from Redis

### 3. API Endpoints (`web/pgadmin/tools/sqleditor/__init__.py`)

Added three new endpoints:

#### `POST /sqleditor/execute_sql_async/<trans_id>`
Submits SQL execution as an async task.

**Request:**
```json
{
  "sql": "SELECT * FROM users;",
  "explain_plan": null
}
```

**Response:**
```json
{
  "data": {
    "task_id": "abc123-def456",
    "status": "Queued"
  }
}
```

#### `GET /sqleditor/task/<task_id>/status`
Returns the current status of a task.

**Response:**
```json
{
  "data": {
    "task_id": "abc123-def456",
    "status": "Busy",
    "job_status": "started"
  }
}
```

Status values:
- `Queued` - Task waiting in queue
- `Busy` - Task currently executing
- `Success` - Task completed successfully
- `Error` - Task failed
- `Deferred` - Task deferred
- `Scheduled` - Task scheduled for later
- `Stopped` - Task stopped

#### `GET /sqleditor/task/<task_id>/result`
Returns the result of a completed task.

**Success Response:**
```json
{
  "data": {
    "status": "Success",
    "result": [[...]],
    "rows_affected": 10,
    "additional_messages": null,
    "notifies": null,
    "colinfo": {...},
    "transaction_status": 0
  }
}
```

**Error Response:**
```json
{
  "success": 0,
  "errormsg": "Connection to the server has been lost.",
  "status": 500
}
```

### 4. Frontend Poller (`web/pgadmin/tools/sqleditor/static/js/components/SqlTaskPoller.js`)

New JavaScript class for frontend task polling:

```javascript
import SqlTaskPoller from './SqlTaskPoller';

const poller = new SqlTaskPoller(api, transId);

// Submit task
const taskData = await poller.submitTask(sql, explainObject);

// Poll for result
await poller.pollForResult(
  (result) => { /* handle success */ },
  (explain) => { /* handle explain */ },
  (error) => { /* handle error */ },
  explainObject,
  flags
);
```

Features:
- Adaptive polling delay (starts at 1s, increases to 5s for long queries)
- Automatic task submission and result retrieval
- Error handling and cancellation support
- Compatible with existing QueryToolComponent event system

## Deployment Requirements

### 1. Redis Server
Ensure Redis is running and accessible:
```bash
redis-server
```

### 2. RQ Worker
Start RQ worker process:
```bash
cd web
rq worker sqleditor_sql_execution --url redis://localhost:6379/0
```

Or with custom settings:
```bash
rq worker sqleditor_sql_execution --url $REDIS_URL --timeout 300
```

### 3. Python Dependencies
Add to `requirements.txt`:
```
redis>=4.0.0
rq>=1.10.0
```

## Migration Notes

### Backward Compatibility
- Existing `/sqleditor/query_tool_start` and `/sqleditor/poll` endpoints remain unchanged
- New async endpoints are additive, not replacements
- Frontend can gradually migrate to new polling mechanism

### Session Management
- Task results stored in Redis with configurable TTL (default: 1 hour)
- No changes to Flask session storage
- Connection parameters serialized and passed to task

### Error Handling
- Connection lost errors returned as task results
- Task timeout after configured limit (default: 5 minutes)
- Failed tasks accessible via `/task/<task_id>/result` for debugging

## Performance Benefits

1. **Scalability**: RQ workers can be scaled horizontally
2. **Resource Management**: No thread pool exhaustion from long queries
3. **Reliability**: Redis persistence for task state
4. **Monitoring**: RQ dashboard for task queue monitoring
5. **Flexibility**: Easy to add priority queues or retry logic

## Testing

### Manual Testing
1. Start Redis server
2. Start RQ worker
3. Submit SQL query via new endpoint
4. Monitor task status
5. Retrieve results

### Example curl commands:
```bash
# Submit task
curl -X POST http://localhost:5050/sqleditor/execute_sql_async/12345 \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT pg_sleep(2);"}'

# Check status
curl http://localhost:5050/sqleditor/task/<task_id>/status

# Get result
curl http://localhost:5050/sqleditor/task/<task_id>/result
```
