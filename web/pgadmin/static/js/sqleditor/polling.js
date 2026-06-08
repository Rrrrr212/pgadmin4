function pollTask(taskId) {
    const statusUrl = `/sqleditor/task/${taskId}/status`;
    const resultUrl = `/sqleditor/task/${taskId}/result`;

    const interval = setInterval(() => {
        fetch(statusUrl)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'finished') {
                    clearInterval(interval);
                    fetch(resultUrl)
                        .then(res => res.json())
                        .then(resultData => {
                            console.log("Task result:", resultData);
                        });
                } else if (data.status === 'failed') {
                    clearInterval(interval);
                    console.error("Task failed");
                }
            })
            .catch(error => {
                clearInterval(interval);
                console.error("Error polling task status:", error);
            });
    }, 2000);
}

function executeSqlAsync(sql) {
    fetch('/sqleditor/execute_sql', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sql: sql })
    })
    .then(response => response.json())
    .then(data => {
        if (data.task_id) {
            pollTask(data.task_id);
        }
    })
    .catch(error => console.error("Error executing SQL:", error));
}