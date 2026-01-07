// Chat Interface Functionality

console.log('[Chat] Initializing chat mode');

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Chat] DOM loaded, setting up chat controls');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const clearBtn = document.getElementById('clear-chat-btn');
    const chatHistory = document.getElementById('chat-history');
    const modelSelect = document.getElementById('chat-model-select');

    // Example prompts
    document.querySelectorAll('.example-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const prompt = btn.dataset.prompt;
            console.log('[Chat] Example prompt clicked:', prompt);
            chatInput.value = prompt;
            sendBtn.click();
        });
    });

    // Send message
    sendBtn.addEventListener('click', async () => {
        const message = chatInput.value.trim();
        if (!message) return;

        const model = modelSelect.value;
        const endpoint = model === 'compare' ? '/chat/compare' : '/chat/send';

        console.log('[Chat] Sending message:', { message: message.substring(0, 50) + '...', model });

        // Add user message to UI immediately
        appendMessage('user', message);
        chatInput.value = '';
        sendBtn.disabled = true;

        // Show thinking indicator
        const modelName = model === 'a' ? 'Model A' : model === 'b' ? 'Model B' : 'Both Models';
        showThinkingIndicator(modelName);

        const startTime = performance.now();
        try {
            const result = await api.post(endpoint, { message, model });
            const duration = performance.now() - startTime;
            console.log(`[Chat] Response received in ${(duration / 1000).toFixed(2)}s`);

            // Remove thinking indicator
            removeThinkingIndicator();

            if (result.error) {
                console.error('[Chat] Chat request failed:', result.error);
                appendMessage('assistant', `Error: ${result.error}`, 'Error');
            } else if (model === 'compare') {
                console.log('[Chat] Comparison response received');
                appendComparisonMessage(result);
            } else {
                console.log('[Chat] Single model response received');
                appendMessage('assistant', result.response, result.model_used);
            }
        } catch (error) {
            console.error('[Chat] Chat request exception:', error);
            // Remove thinking indicator on error too
            removeThinkingIndicator();
            appendMessage('assistant', `Error: ${error.message}`, 'Error');
        } finally {
            sendBtn.disabled = false;
            scrollToBottom();
        }
    });

    // Enter key to send (Shift+Enter for new line)
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendBtn.click();
        }
    });

    // Clear history
    clearBtn.addEventListener('click', async () => {
        if (confirm('Clear chat history?')) {
            console.log('[Chat] Clearing chat history');
            await api.post('/chat/clear', {});
            chatHistory.innerHTML = '';
            console.log('[Chat] Chat history cleared');
        }
    });

    // Scroll to bottom on page load
    scrollToBottom();
    console.log('[Chat] Event listeners configured');
});

function appendMessage(role, content, model = '') {
    const chatHistory = document.getElementById('chat-history');
    const timestamp = new Date().toLocaleTimeString();

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}-message`;

    messageDiv.innerHTML = `
        <div class="message-content">${escapeHtml(content)}</div>
        <div class="message-meta">
            ${timestamp}${model ? ' • ' + model : ''}
        </div>
    `;

    chatHistory.appendChild(messageDiv);
}

function appendComparisonMessage(result) {
    const chatHistory = document.getElementById('chat-history');
    const timestamp = new Date().toLocaleTimeString();

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant-message';
    messageDiv.style.maxWidth = '90%';

    const modelA = result.model_a || {};
    const modelB = result.model_b || {};

    messageDiv.innerHTML = `
        <div style="margin-bottom: 15px;">
            <strong style="color: var(--primary-color);">Model A:</strong>
            <div class="message-content">${escapeHtml(modelA.response || '')}</div>
            <div class="message-meta">Latency: ${(modelA.latency_seconds || 0).toFixed(2)}s</div>
        </div>
        <hr style="margin: 10px 0;">
        <div>
            <strong style="color: var(--primary-color);">Model B:</strong>
            <div class="message-content">${escapeHtml(modelB.response || '')}</div>
            <div class="message-meta">Latency: ${(modelB.latency_seconds || 0).toFixed(2)}s</div>
        </div>
        <div class="message-meta" style="margin-top: 10px">${timestamp} • Comparison</div>
    `;

    chatHistory.appendChild(messageDiv);
}

function scrollToBottom() {
    const chatHistory = document.getElementById('chat-history');
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showThinkingIndicator(modelName) {
    const chatHistory = document.getElementById('chat-history');

    const thinkingDiv = document.createElement('div');
    thinkingDiv.id = 'thinking-indicator-message';
    thinkingDiv.className = 'message thinking-message';

    thinkingDiv.innerHTML = `
        <div class="message-content">
            <span style="color: var(--text-secondary); margin-right: 8px;">${modelName} is thinking</span>
            <div class="thinking-indicator">
                <div class="thinking-dot"></div>
                <div class="thinking-dot"></div>
                <div class="thinking-dot"></div>
            </div>
        </div>
    `;

    chatHistory.appendChild(thinkingDiv);
    scrollToBottom();
}

function removeThinkingIndicator() {
    const thinkingDiv = document.getElementById('thinking-indicator-message');
    if (thinkingDiv) {
        thinkingDiv.remove();
    }
}

// ===== Container Logs Functionality =====

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

// Set up logs functionality after DOM loads
document.addEventListener('DOMContentLoaded', () => {
    // Fetch logs button
    document.getElementById('fetch-logs-btn').addEventListener('click', async () => {
        const container = document.getElementById('container-select').value;
        const lines = document.getElementById('log-lines').value;

        console.log('[Chat] Fetching logs:', { container, lines });

        try {
            const data = await api.get(`/api/logs/${container}?lines=${lines}`);
            rawLogs = data.result || 'No logs available';

            const logsDisplay = document.getElementById('logs-display');
            logsDisplay.style.display = 'block';
            updateLogsDisplay();

            const totalLines = rawLogs.split('\n').filter(l => l.trim()).length;
            console.log(`[Chat] Fetched ${totalLines} lines of logs`);
        } catch (error) {
            console.error('[Chat] Failed to fetch logs:', error);
            alert(`Error fetching logs: ${error.message}`);
        }
    });

    // Toggle filter
    document.getElementById('filter-health-checks').addEventListener('change', () => {
        console.log('[Chat] Monitoring/polling logs filter toggled');
        updateLogsDisplay();
    });

    console.log('[Chat] Logs functionality initialized');
});
