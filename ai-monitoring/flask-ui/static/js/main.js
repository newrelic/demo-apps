// AI Monitoring Demo - Global JavaScript Utilities

console.log('[Main] Initializing global utilities');

// Global API client
class APIClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
        console.log('[APIClient] Initialized with baseUrl:', baseUrl);
    }

    async get(endpoint) {
        console.log('[APIClient] GET request:', endpoint);
        const startTime = performance.now();
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`);
            const duration = performance.now() - startTime;
            console.log(`[APIClient] GET ${endpoint} completed in ${duration.toFixed(2)}ms with status ${response.status}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const data = await response.json();
            console.log('[APIClient] Response data:', data);
            return data;
        } catch (error) {
            console.error(`[APIClient] GET ${endpoint} failed:`, error);
            return { error: error.message };
        }
    }

    async post(endpoint, data) {
        console.log('[APIClient] POST request:', endpoint, 'with data:', data);
        const startTime = performance.now();
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const duration = performance.now() - startTime;
            console.log(`[APIClient] POST ${endpoint} completed in ${duration.toFixed(2)}ms with status ${response.status}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const responseData = await response.json();
            console.log('[APIClient] Response data:', responseData);
            return responseData;
        } catch (error) {
            console.error(`[APIClient] POST ${endpoint} failed:`, error);
            return { error: error.message };
        }
    }
}

// Global API client instance
const api = new APIClient();

// Polling manager
class PollingManager {
    constructor() {
        this.intervals = new Map();
    }

    start(key, callback, intervalMs) {
        if (this.intervals.has(key)) {
            this.stop(key);
        }
        const id = setInterval(callback, intervalMs);
        this.intervals.set(key, id);
        callback(); // Execute immediately
    }

    stop(key) {
        if (this.intervals.has(key)) {
            clearInterval(this.intervals.get(key));
            this.intervals.delete(key);
        }
    }

    stopAll() {
        this.intervals.forEach(id => clearInterval(id));
        this.intervals.clear();
    }
}

// Global polling manager instance
const polling = new PollingManager();
console.log('[Main] PollingManager initialized');

// Sidebar auto-update (agent health, quick stats)
async function updateSidebar() {
    console.log('[Main] Updating sidebar data');
    // Update agent status
    const healthData = await api.get('/api/health');
    const statusEl = document.getElementById('agent-status');

    if (statusEl) {
        if (healthData.error) {
            console.warn('[Main] Agent health check failed:', healthData.error);
            statusEl.innerHTML = '<div class="status-error">❌ Agent: Offline</div>';
        } else {
            const hours = Math.floor(healthData.uptime_seconds / 3600);
            const minutes = Math.floor((healthData.uptime_seconds % 3600) / 60);
            console.log(`[Main] Agent status: Online (uptime: ${hours}h ${minutes}m)`);
            statusEl.innerHTML = `
                <div class="status-success">✅ Agent: Online</div>
                <div class="status-uptime">Uptime: ${hours}h ${minutes}m</div>
            `;
        }
    }

    // Update quick stats
    const metricsData = await api.get('/api/metrics');
    const statsEl = document.getElementById('quick-stats');

    if (statsEl && !metricsData.error) {
        console.log('[Main] Quick stats updated:', {
            modelA: metricsData.model_a.total_requests,
            modelB: metricsData.model_b.total_requests
        });
        statsEl.innerHTML = `
            <h3>Quick Stats</h3>
            <div class="stat">Model A: ${metricsData.model_a.total_requests} requests</div>
            <div class="stat">Model B: ${metricsData.model_b.total_requests} requests</div>
        `;
    } else if (metricsData.error) {
        console.warn('[Main] Failed to fetch metrics:', metricsData.error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('[Main] DOM loaded, initializing application');
    // Start sidebar polling (every 30 seconds)
    polling.start('sidebar', updateSidebar, 30000);
    console.log('[Main] Sidebar polling started (30s interval)');
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    console.log('[Main] Page unloading, cleaning up polling intervals');
    polling.stopAll();
});
