// Chat Interface Functionality

console.log('[Chat] Initializing chat mode');

// Store prompts globally
let availablePrompts = [];

document.addEventListener('DOMContentLoaded', () => {
    console.log('[Chat] DOM loaded, setting up chat controls');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const clearBtn = document.getElementById('clear-chat-btn');
    const chatHistory = document.getElementById('chat-history');
    const modelSelect = document.getElementById('chat-model-select');

    // Prompt selection elements
    const promptSelect = document.getElementById('prompt-select');
    const loadPromptBtn = document.getElementById('load-prompt-btn');
    const randomPromptBtn = document.getElementById('random-prompt-btn');
    const promptPreview = document.getElementById('prompt-preview');
    const promptCategory = document.getElementById('prompt-category');
    const promptDescription = document.getElementById('prompt-description');
    const promptText = document.getElementById('prompt-text');

    // Load prompts on page load
    loadPrompts();

    // Load prompts from API
    async function loadPrompts() {
        try {
            console.log('[Chat] Loading prompts from API...');
            const response = await api.get('/chat/prompts');

            if (response.success && response.prompts) {
                availablePrompts = response.prompts;
                console.log(`[Chat] Loaded ${availablePrompts.length} prompts`);

                // Populate dropdown
                promptSelect.innerHTML = '<option value="">-- Select a prompt --</option>';
                availablePrompts.forEach((p, idx) => {
                    const option = document.createElement('option');
                    option.value = idx;
                    option.textContent = `[${p.category}] ${p.preview}`;
                    promptSelect.appendChild(option);
                });
            } else {
                console.error('[Chat] Failed to load prompts:', response.error);
                promptSelect.innerHTML = '<option value="">Error loading prompts</option>';
            }
        } catch (error) {
            console.error('[Chat] Error loading prompts:', error);
            promptSelect.innerHTML = '<option value="">Error loading prompts</option>';
        }
    }

    // Preview prompt when selection changes
    promptSelect.addEventListener('change', () => {
        const idx = parseInt(promptSelect.value);
        if (isNaN(idx) || idx < 0 || idx >= availablePrompts.length) {
            promptPreview.style.display = 'none';
            return;
        }

        const prompt = availablePrompts[idx];
        promptCategory.textContent = prompt.category;
        promptDescription.textContent = prompt.description;
        promptText.textContent = prompt.prompt;
        promptPreview.style.display = 'block';

        console.log('[Chat] Prompt preview:', prompt.category);
    });

    // Load selected prompt into input
    loadPromptBtn.addEventListener('click', () => {
        const idx = parseInt(promptSelect.value);
        if (isNaN(idx) || idx < 0 || idx >= availablePrompts.length) {
            alert('Please select a prompt first');
            return;
        }

        const prompt = availablePrompts[idx];
        chatInput.value = prompt.prompt;
        console.log('[Chat] Loaded prompt into input:', prompt.category);
    });

    // Load random prompt
    randomPromptBtn.addEventListener('click', () => {
        if (availablePrompts.length === 0) {
            alert('No prompts available');
            return;
        }

        const randomIdx = Math.floor(Math.random() * availablePrompts.length);
        promptSelect.value = randomIdx;
        promptSelect.dispatchEvent(new Event('change'));

        const prompt = availablePrompts[randomIdx];
        chatInput.value = prompt.prompt;
        console.log('[Chat] Random prompt loaded:', prompt.category);
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
