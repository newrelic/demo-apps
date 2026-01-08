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

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    console.log('[Main] Page unloading, cleaning up polling intervals');
    polling.stopAll();
});
