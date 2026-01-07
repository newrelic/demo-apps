// Repair Mode Functionality

console.log('[Repair] Initializing repair mode');

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Repair] DOM loaded, setting up repair mode controls');
    const triggerBtn = document.getElementById('trigger-repair-btn');
    const modelSelect = document.getElementById('model-select');
    const progressDiv = document.getElementById('repair-progress');
    const resultsSection = document.getElementById('repair-results');
    const resultsContent = document.getElementById('results-content');

    // Container status polling
    function updateContainerStatus() {
        console.log('[Repair] Updating container status');
        api.get('/api/containers').then(data => {
            if (data.error) {
                document.getElementById('container-grid').innerHTML =
                    `<div class="error">Error: ${data.error}</div>`;
                return;
            }

            try {
                const containers = JSON.parse(data.result || '[]');
                console.log(`[Repair] Found ${containers.length} containers`);
                const grid = document.getElementById('container-grid');
                grid.innerHTML = containers.map(c => {
                    const statusIcon = c.status === 'running' ? '🟢' :
                                       c.status === 'exited' || c.status === 'dead' ? '🔴' : '🟡';
                    return `
                        <div class="container-card">
                            <div class="container-name">${c.name.replace('aim-', '')}</div>
                            <div class="container-status">${statusIcon} ${c.status}</div>
                            <div class="container-uptime">⏱️ ${c.uptime || 'unknown'}</div>
                        </div>
                    `;
                }).join('');
            } catch (e) {
                console.error('Failed to parse containers:', e);
            }
        });
    }

    // Start polling containers (every 15 seconds)
    polling.start('containers', updateContainerStatus, 15000);
    console.log('[Repair] Container status polling started (15s interval)');

    // Refresh button
    document.getElementById('refresh-status-btn').addEventListener('click', updateContainerStatus);

    // Trigger repair
    triggerBtn.addEventListener('click', async () => {
        const model = modelSelect.value;
        const endpoint = model === 'compare' ? '/repair/compare' : '/repair/trigger';
        const params = model === 'compare' ? {} : { model };

        console.log('[Repair] Triggering repair workflow:', { model, endpoint });

        // Show progress
        triggerBtn.disabled = true;
        progressDiv.style.display = 'block';
        resultsSection.style.display = 'none';

        const startTime = performance.now();
        try {
            const result = await api.post(endpoint, params);
            const duration = performance.now() - startTime;
            console.log(`[Repair] Repair workflow completed in ${(duration / 1000).toFixed(2)}s`);

            // Hide progress
            progressDiv.style.display = 'none';
            triggerBtn.disabled = false;

            // Display results
            resultsSection.style.display = 'block';
            resultsContent.innerHTML = renderRepairResults(result, model === 'compare');

        } catch (error) {
            console.error('[Repair] Repair workflow failed:', error);
            progressDiv.style.display = 'none';
            triggerBtn.disabled = false;

            // Display error in results section instead of alert
            resultsSection.style.display = 'block';
            resultsContent.innerHTML = renderErrorMessage(error.message || 'Unknown error occurred');
        }
    });

    // Store raw logs for filtering
    let rawLogs = '';

    // Filter logs based on checkbox
    function filterLogs(logs) {
        const filterHealthChecks = document.getElementById('filter-health-checks').checked;

        if (!filterHealthChecks) {
            return logs;
        }

        // Filter out health check and monitoring/polling related log lines
        const lines = logs.split('\n');
        const filtered = lines.filter(line => {
            const lowerLine = line.toLowerCase();

            // Filter patterns for health checks
            if (lowerLine.includes('get /health') ||
                lowerLine.includes('get /api/health') ||
                lowerLine.includes('head /health') ||
                lowerLine.includes('"get /health http') ||
                lowerLine.includes('health check') ||
                (lowerLine.includes('/health') && lowerLine.includes('200'))) {
                return false;
            }

            // Filter patterns for metrics/stats polling
            if (lowerLine.includes('get /metrics') ||
                lowerLine.includes('"get /metrics http') ||
                lowerLine.includes('get /stats/requests') ||
                lowerLine.includes('/tools/locust_get_stats') ||
                lowerLine.includes('retrieved load test results')) {
                return false;
            }

            // Filter patterns for Ollama model polling
            if (lowerLine.includes('[gin]') && lowerLine.includes('get') && lowerLine.includes('/api/tags')) {
                return false;
            }

            // Filter httpx requests to locust stats
            if (lowerLine.includes('httpx') && lowerLine.includes('http request: get') &&
                lowerLine.includes('locust') && lowerLine.includes('/stats')) {
                return false;
            }

            return true;
        });

        return filtered.join('\n');
    }

    // Update logs display with current filter
    function updateLogsDisplay() {
        const logsDisplay = document.getElementById('logs-display');
        if (rawLogs) {
            const filtered = filterLogs(rawLogs);
            logsDisplay.textContent = filtered || 'No logs available (all filtered out)';

            // Show count of filtered lines
            const totalLines = rawLogs.split('\n').filter(l => l.trim()).length;
            const filteredLines = filtered.split('\n').filter(l => l.trim()).length;
            const hiddenCount = totalLines - filteredLines;

            if (hiddenCount > 0 && document.getElementById('filter-health-checks').checked) {
                logsDisplay.textContent = `[Filtered out ${hiddenCount} monitoring/polling log line(s)]\n\n` + filtered;
            }
        }
    }

    // Fetch logs
    document.getElementById('fetch-logs-btn').addEventListener('click', async () => {
        const container = document.getElementById('container-select').value;
        const lines = document.getElementById('log-lines').value;

        console.log('[Repair] Fetching logs:', { container, lines });

        try {
            const data = await api.get(`/api/logs/${container}?lines=${lines}`);
            rawLogs = data.result || 'No logs available';

            const logsDisplay = document.getElementById('logs-display');
            logsDisplay.style.display = 'block';
            updateLogsDisplay();

            const totalLines = rawLogs.split('\n').filter(l => l.trim()).length;
            console.log(`[Repair] Fetched ${totalLines} lines of logs`);
        } catch (error) {
            console.error('[Repair] Failed to fetch logs:', error);
            alert(`Error fetching logs: ${error.message}`);
        }
    });

    // Toggle filter
    document.getElementById('filter-health-checks').addEventListener('change', () => {
        console.log('[Repair] Monitoring/polling logs filter toggled');
        updateLogsDisplay();
    });

    console.log('[Repair] Event listeners configured');
});

function renderRepairResults(result, isComparison) {
    if (result.error) {
        return renderErrorMessage(result.error);
    }

    if (isComparison) {
        return renderComparisonResults(result);
    } else {
        return renderSingleRepairResults(result);
    }
}

function renderErrorMessage(errorMsg) {
    let title = "Something Went Wrong";
    let explanation = "";
    let suggestions = [];

    // Parse different error types and provide helpful explanations
    if (errorMsg.includes("Timeout") || errorMsg.includes("timeout") || errorMsg.includes("exceeded") && errorMsg.includes("minute")) {
        title = "AI Agent Took Too Long";
        explanation = "The AI Agent started working on the repair but didn't finish within 3 minutes. " +
                     "This usually means the model got stuck in a loop, kept retrying failed actions, or couldn't produce the right output format after many attempts. " +
                     "Looking at your logs, the agent made 3 restart attempts over 70 seconds, then likely got stuck trying to format its final response.";
        suggestions = [
            "Check the AI Agent logs for the complete story: <code>docker logs aim-ai-agent --tail 100</code> (you may need more than 50 lines)",
            "Look for repeated tool calls or 'Invalid JSON' errors in the logs",
            "The model may be stuck in a validation retry loop - check for 'Exceeded maximum retries' messages",
            "Try using Model B instead (sometimes it's faster at structured output)",
            "Restart the AI Agent if it seems stuck: <code>docker-compose restart ai-agent</code>"
        ];
    } else if (errorMsg.includes("output validation") || errorMsg.includes("UnexpectedModelBehavior") ||
        errorMsg.includes("Invalid JSON") || errorMsg.includes("Exceeded maximum retries")) {
        title = "AI Model Can't Follow Instructions";
        explanation = "The Ollama model tried to help, but kept returning conversational text instead of the structured data format it needs to return. " +
                     "This is like asking someone to fill out a form, but they just write you a letter instead. " +
                     "Small language models (like llama3.2:1b and qwen2.5:0.5b) often struggle with structured output.";
        suggestions = [
            "Try running the repair again - sometimes it works on the second try",
            "Try using Model B instead (it's smaller but sometimes better at following format rules)",
            "Check the AI Agent logs to see the exact text the model returned: <code>docker logs aim-ai-agent --tail 100</code>",
            "The model may be overloaded - check memory: <code>docker stats aim-ollama-model-a aim-ollama-model-b</code>",
            "Consider using a larger, more capable model if this persists"
        ];
    } else if (errorMsg.includes("Connection failed") || errorMsg.includes("Unable to reach") ||
               errorMsg.includes("Failed to fetch")) {
        title = "Can't Reach AI Agent";
        explanation = "The Flask UI couldn't communicate with the AI Agent service. " +
                     "This could mean the agent isn't running, crashed during the repair, or took too long to respond. " +
                     "If you saw the repair working in the logs before this error, it likely timed out or got stuck.";
        suggestions = [
            "Check if the AI Agent container is still running: <code>docker ps | grep ai-agent</code>",
            "Look at the FULL AI Agent logs (not just 50 lines): <code>docker logs aim-ai-agent --tail 150</code>",
            "Look for 'Exceeded maximum retries' or timeout messages in the logs",
            "If the agent is stuck, restart it: <code>docker-compose restart ai-agent</code>",
            "Try the repair again - the agent might recover"
        ];
    } else if (errorMsg.includes("500")) {
        title = "AI Agent Had an Internal Problem";
        explanation = "The AI Agent service crashed or encountered an error while trying to fix the system. " +
                     "This is like asking your friend for help, and they tried but something went wrong on their end.";
        suggestions = [
            "Check the AI Agent logs for errors: <code>docker logs aim-ai-agent --tail 50</code>",
            "Check if the Ollama models are running: <code>docker ps | grep ollama</code>",
            "The models might be out of memory - check: <code>docker stats aim-ollama-model-a aim-ollama-model-b</code>",
            "Try restarting the AI Agent: <code>docker-compose restart ai-agent</code>"
        ];
    } else if (errorMsg.includes("timeout") || errorMsg.includes("Timeout")) {
        title = "AI Agent Took Too Long to Respond";
        explanation = "The AI Agent started working on the repair but took longer than expected (usually over 2 minutes). " +
                     "This is like asking someone a question and they're still thinking after 5 minutes.";
        suggestions = [
            "The Ollama models might be overloaded or slow",
            "Check model memory usage: <code>docker stats aim-ollama-model-a aim-ollama-model-b</code>",
            "Look at AI Agent logs to see what it's doing: <code>docker logs aim-ai-agent --tail 50</code>",
            "Try using Model B instead (it's faster but less powerful)"
        ];
    } else if (errorMsg.includes("404")) {
        title = "AI Agent Endpoint Not Found";
        explanation = "The Flask UI tried to reach a specific part of the AI Agent, but that endpoint doesn't exist. " +
                     "This is like calling the right phone number but asking for the wrong person.";
        suggestions = [
            "This might be a bug in the Flask UI code",
            "Check if the AI Agent is running the latest version: <code>docker-compose build ai-agent</code>",
            "Restart both Flask UI and AI Agent: <code>docker-compose restart flask-ui ai-agent</code>"
        ];
    } else {
        title = "Unexpected Error";
        explanation = `The repair workflow failed with this error: "${errorMsg}". ` +
                     "This could be caused by various issues with the services.";
        suggestions = [
            "Check all container statuses: <code>docker-compose ps</code>",
            "Look at AI Agent logs: <code>docker logs aim-ai-agent --tail 50</code>",
            "Check Flask UI logs: <code>docker logs aim-flask-ui --tail 50</code>",
            "Try refreshing the page and running the repair again"
        ];
    }

    return `
        <div class="repair-result error">
            <h3>❌ ${title}</h3>
            <div class="error-explanation">
                <h4>What Happened:</h4>
                <p>${explanation}</p>
            </div>
            <div class="error-suggestions">
                <h4>How to Fix It:</h4>
                <ol>
                    ${suggestions.map(s => `<li>${s}</li>`).join('')}
                </ol>
            </div>
            <div class="error-details">
                <details>
                    <summary>Technical Details (for debugging)</summary>
                    <pre>${errorMsg}</pre>
                </details>
            </div>
        </div>
    `;
}

function renderSingleRepairResults(result) {
    // Check if this is a validation error (model returning wrong format)
    if (!result.success && result.final_status &&
        (result.final_status.includes('output validation') ||
         result.final_status.includes('UnexpectedModelBehavior') ||
         result.final_status.includes('Invalid JSON') ||
         result.final_status.includes('Exceeded maximum retries'))) {
        // Show user-friendly error message for validation failures
        return renderErrorMessage(result.final_status);
    }

    const statusClass = result.success ? 'success' : 'error';
    const statusIcon = result.success ? '✅' : '❌';

    // Render tool calls if available
    const toolCallsHtml = (result.tool_calls && result.tool_calls.length > 0) ? `
        <div class="tool-calls">
            <h4>🔧 MCP Tool Invocations:</h4>
            <div class="tool-calls-list">
                ${result.tool_calls.map(tc => {
                    const tcIcon = tc.success ? '✅' : '❌';
                    const tcClass = tc.success ? 'tool-call-success' : 'tool-call-error';
                    const argsStr = Object.keys(tc.arguments).length > 0
                        ? `(${Object.entries(tc.arguments).map(([k, v]) => `${k}=${v}`).join(', ')})`
                        : '()';
                    return `
                        <div class="tool-call ${tcClass}">
                            <div class="tool-call-header">
                                ${tcIcon} <strong>${tc.tool_name}</strong>${argsStr}
                            </div>
                            ${tc.result ? `<div class="tool-call-result">${escapeHtml(tc.result)}</div>` : ''}
                            ${tc.error ? `<div class="tool-call-error-msg">Error: ${escapeHtml(tc.error)}</div>` : ''}
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
    ` : '';

    return `
        <div class="repair-result ${statusClass}">
            <h3>${statusIcon} ${result.success ? 'Success' : 'Failed'}</h3>
            <div class="metrics">
                <div class="metric"><strong>Model:</strong> ${result.model_used}</div>
                <div class="metric"><strong>Latency:</strong> ${result.latency_seconds.toFixed(2)}s</div>
                <div class="metric"><strong>Containers Restarted:</strong> ${(result.containers_restarted || []).length}</div>
                <div class="metric"><strong>Tool Calls:</strong> ${(result.tool_calls || []).length}</div>
            </div>
            <p><strong>Final Status:</strong> ${result.final_status}</p>
            ${toolCallsHtml}
            <div class="actions">
                <h4>Actions Taken:</h4>
                <ul>
                    ${result.actions_taken.map(a => `<li>${a}</li>`).join('')}
                </ul>
            </div>
        </div>
    `;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderComparisonResults(result) {
    const modelA = result.model_a_result || {};
    const modelB = result.model_b_result || {};

    return `
        <div class="comparison-grid">
            <div class="comparison-column">
                <h3>Model A Results</h3>
                ${renderSingleRepairResults(modelA)}
            </div>
            <div class="comparison-column">
                <h3>Model B Results</h3>
                ${renderSingleRepairResults(modelB)}
            </div>
        </div>
        <div class="repair-result">
            <h3>🏆 Comparison Summary</h3>
            <p><strong>Winner:</strong> ${result.winner === 'a' ? 'Model A' : result.winner === 'b' ? 'Model B' : 'Tie'}</p>
            <p><strong>Reason:</strong> ${result.reason || 'N/A'}</p>
        </div>
    `;
}
