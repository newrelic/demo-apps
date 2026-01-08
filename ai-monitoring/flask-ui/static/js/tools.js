// Tools Mode Functionality

console.log('[Tools] Initializing tools mode');

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Tools] DOM loaded, setting up tools mode controls');
    const triggerBtn = document.getElementById('trigger-repair-btn');
    const modelSelect = document.getElementById('model-select');
    const progressDiv = document.getElementById('repair-progress');
    const resultsSection = document.getElementById('repair-results');
    const resultsContent = document.getElementById('results-content');

    const streamSection = document.getElementById('execution-stream');
    const streamContent = document.getElementById('stream-content');

    // Trigger tool execution
    triggerBtn.addEventListener('click', async () => {
        const model = modelSelect.value;
        const endpoint = '/tools/trigger';
        const params = { model };

        console.log('[Tools] Triggering tool execution workflow:', { model, endpoint });

        // Show progress and stream
        triggerBtn.disabled = true;
        progressDiv.style.display = 'block';
        resultsSection.style.display = 'none';
        streamSection.style.display = 'block';
        streamContent.innerHTML = '';

        // Add initial log
        addStreamLog('🚀 Starting tool execution workflow...', 'info');
        addStreamLog(`📋 Model selected: ${model === 'a' ? 'Model A (mistral:7b-instruct)' : 'Model B (ministral-3:8b)'}`, 'info');

        const startTime = performance.now();
        try {
            const result = await api.post(endpoint, params);
            const duration = performance.now() - startTime;
            console.log(`[Tools] Tool execution workflow completed in ${(duration / 1000).toFixed(2)}s`);

            // Simulate progressive display of tool calls
            await displayProgressiveLogs(result);

            // Hide progress
            progressDiv.style.display = 'none';
            triggerBtn.disabled = false;

            // Display results
            resultsSection.style.display = 'block';
            resultsContent.innerHTML = renderToolResults(result);

            // Final log entry
            if (result.success) {
                addStreamLog(`✅ Workflow completed successfully in ${(duration / 1000).toFixed(2)}s`, 'success');
            } else {
                addStreamLog('❌ Workflow completed with errors', 'error');
            }

        } catch (error) {
            console.error('[Tools] Tool execution workflow failed:', error);
            progressDiv.style.display = 'none';
            triggerBtn.disabled = false;

            addStreamLog(`❌ Error: ${error.message || 'Unknown error occurred'}`, 'error');

            // Display error in results section instead of alert
            resultsSection.style.display = 'block';
            resultsContent.innerHTML = renderErrorMessage(error.message || 'Unknown error occurred');
        }
    });

    function addStreamLog(message, type = 'info') {
        const logEntry = document.createElement('div');
        logEntry.className = `stream-log stream-log-${type}`;

        const timestamp = new Date().toLocaleTimeString();
        logEntry.innerHTML = `
            <span class="stream-timestamp">[${timestamp}]</span>
            <span class="stream-message">${escapeHtml(message)}</span>
        `;

        streamContent.appendChild(logEntry);
        streamContent.scrollTop = streamContent.scrollHeight;
    }

    async function displayProgressiveLogs(result) {
        const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

        // Display model info
        if (result.model_used) {
            addStreamLog(`🤖 Using model: ${result.model_used}`, 'info');
            await delay(300);
        }

        // Display AI reasoning/analysis
        if (result.ai_reasoning) {
            await delay(400);
            addStreamLog('🧠 AI Analysis:', 'info');
            await delay(200);

            // Split reasoning into sentences for better display
            const sentences = result.ai_reasoning.split(/[.!?]+/).filter(s => s.trim());
            for (const sentence of sentences.slice(0, 3)) { // Show first 3 sentences
                if (sentence.trim()) {
                    addStreamLog(`   ${sentence.trim()}.`, 'action');
                    await delay(300);
                }
            }

            await delay(400);
            addStreamLog('📋 Beginning tool execution based on analysis...', 'info');
            await delay(300);
        }

        // Display tool calls progressively
        if (result.tool_calls && result.tool_calls.length > 0) {
            addStreamLog(`🔧 Executing ${result.tool_calls.length} tool call(s)...`, 'info');
            await delay(400);

            for (const toolCall of result.tool_calls) {
                const args = Object.keys(toolCall.arguments).length > 0
                    ? `(${Object.entries(toolCall.arguments).map(([k, v]) => `${k}=${v}`).join(', ')})`
                    : '()';

                addStreamLog(`🔨 Calling ${toolCall.tool_name}${args}`, 'tool');
                await delay(400);

                if (toolCall.success) {
                    const resultPreview = toolCall.result ?
                        (toolCall.result.length > 100 ? toolCall.result.substring(0, 100) + '...' : toolCall.result) :
                        'Success';
                    addStreamLog(`  ✓ ${toolCall.tool_name} completed: ${resultPreview}`, 'success');
                } else {
                    const errorMsg = toolCall.error || 'Unknown error';
                    addStreamLog(`  ✗ ${toolCall.tool_name} failed: ${errorMsg}`, 'error');
                }
                await delay(300);
            }
        }

        // Display actions taken
        if (result.actions_taken && result.actions_taken.length > 0) {
            await delay(400);
            addStreamLog('📝 Actions taken:', 'info');
            await delay(200);
            for (const action of result.actions_taken) {
                addStreamLog(`  • ${action}`, 'action');
                await delay(250);
            }
        }

        // Display final status
        if (result.final_status) {
            await delay(400);
            addStreamLog(`📊 Status: ${result.final_status}`, result.success ? 'success' : 'warning');
        }

        await delay(300);
    }

    console.log('[Tools] Event listeners configured');
});

function renderToolResults(result) {
    if (result.error) {
        return renderErrorMessage(result.error);
    }

    return renderSingleToolResults(result);
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
                     "Even larger models (like mistral:7b-instruct and ministral-3:8b-instruct-2512-q8_0) can occasionally struggle with structured output.";
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
        <div class="tool-result error">
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

function renderSingleToolResults(result) {
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

    // Render AI reasoning if available
    const aiReasoningHtml = result.ai_reasoning ? `
        <div class="tool-calls">
            <h4>🧠 AI Analysis:</h4>
            <div class="tool-call-result" style="margin-top: 10px;">
                ${escapeHtml(result.ai_reasoning)}
            </div>
        </div>
    ` : '';

    return `
        <div class="tool-result ${statusClass}">
            <h3>${statusIcon} ${result.success ? 'Success' : 'Failed'}</h3>
            <div class="metrics">
                <div class="metric"><strong>Model:</strong> ${result.model_used}</div>
                <div class="metric"><strong>Latency:</strong> ${result.latency_seconds.toFixed(2)}s</div>
                <div class="metric"><strong>Services Affected:</strong> ${(result.containers_restarted || []).length}</div>
                <div class="metric"><strong>Tool Calls:</strong> ${(result.tool_calls || []).length}</div>
            </div>
            <p><strong>Final Status:</strong> ${result.final_status}</p>
            ${aiReasoningHtml}
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
