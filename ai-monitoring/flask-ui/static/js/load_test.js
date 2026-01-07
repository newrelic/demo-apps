// Load Testing Controls

console.log('[LoadTest] Initializing load test controls');

document.addEventListener('DOMContentLoaded', () => {
    console.log('[LoadTest] DOM loaded, setting up event listeners');
    const startBtn = document.getElementById('start-load-test-btn');
    const stopBtn = document.getElementById('stop-load-test-btn');
    const checkBtn = document.getElementById('check-load-test-btn');
    const statusDiv = document.getElementById('load-test-status');

    // Poll load test status every 5 seconds
    polling.start('load-test', updateLoadTestStatus, 5000);
    console.log('[LoadTest] Load test status polling started (5s interval)');

    // Check status button
    if (checkBtn) {
        checkBtn.addEventListener('click', updateLoadTestStatus);
    }

    // Start load test
    if (startBtn) {
        startBtn.addEventListener('click', async () => {
            const users = parseInt(document.getElementById('load-test-users').value);
            const duration = parseInt(document.getElementById('load-test-duration').value);

            console.log('[LoadTest] Starting load test:', { users, duration: `${duration}min` });

            startBtn.disabled = true;
            startBtn.textContent = '⏳ Starting...';

            const result = await api.post('/api/load-test/start', {
                users: users,
                spawn_rate: 2,
                duration: duration * 60
            });

            if (result.error) {
                console.error('[LoadTest] Failed to start load test:', result.error);
                alert(`Error: ${result.error}`);
            } else {
                console.log('[LoadTest] Load test started successfully');
                alert(`✅ Started: ${users} users, ${duration}min`);
                updateLoadTestStatus();
            }

            startBtn.disabled = false;
            startBtn.textContent = '🚀 Start Load Test';
        });
    }

    // Stop load test
    if (stopBtn) {
        stopBtn.addEventListener('click', async () => {
            console.log('[LoadTest] Stopping load test');
            stopBtn.disabled = true;
            stopBtn.textContent = '⏳ Stopping...';

            await api.post('/api/load-test/stop', {});
            console.log('[LoadTest] Load test stopped');
            updateLoadTestStatus();

            stopBtn.disabled = false;
            stopBtn.textContent = '⏹️ Stop Test';
        });
    }

    console.log('[LoadTest] Event listeners configured');
});

async function updateLoadTestStatus() {
    console.log('[LoadTest] Fetching load test status');
    const stats = await api.get('/api/load-test/status');
    const statusDiv = document.getElementById('load-test-status');
    const stopBtn = document.getElementById('stop-load-test-btn');

    if (!statusDiv) return;

    if (stats.error) {
        console.warn('[LoadTest] Error fetching status:', stats.error);
        statusDiv.innerHTML = `<div class="status-error">⚠️ ${stats.error}</div>`;
        if (stopBtn) stopBtn.style.display = 'none';
        return;
    }

    console.log('[LoadTest] Current status:', stats.status, stats);

    if (stats.status === 'running') {
        statusDiv.innerHTML = `
            <div class="status-success">✅ Load test running</div>
            <div class="stat">Requests: ${stats.total_requests || 0}</div>
            <div class="stat">Users: ${stats.user_count || 0}</div>
            <div class="stat">Avg Time: ${(stats.avg_response_time || 0).toFixed(0)}ms</div>
            <div class="stat">RPS: ${(stats.requests_per_second || 0).toFixed(1)}</div>
            <div class="caption">ℹ️ ~10% error rate expected</div>
        `;
        if (stopBtn) stopBtn.style.display = 'block';
    } else if (stats.status === 'stopped') {
        statusDiv.innerHTML = '<div class="status-loading">⏸️ No test running</div>';
        if (stopBtn) stopBtn.style.display = 'none';
    } else {
        statusDiv.innerHTML = `<div class="status-loading">Status: ${stats.status}</div>`;
        if (stopBtn) stopBtn.style.display = 'none';
    }
}
