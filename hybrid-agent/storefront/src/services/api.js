import axios from 'axios';

/**
 * API client for backend services
 * Supports routing to APM, OTel, or Hybrid variants
 */

// Base URLs for different variants
const BACKEND_URLS = {
  apm: 'http://localhost:3000',
  otel: 'http://localhost:3001',
  hybrid: 'http://localhost:3002',
  mixed: 'http://localhost:3000'  // Mixed mode uses port 3000
};

// In Docker environment, use internal service names
const isDocker = window.location.hostname !== 'localhost';

if (isDocker) {
  BACKEND_URLS.apm = 'http://order-service-apm:3000';
  BACKEND_URLS.otel = 'http://order-service-otel:3000';
  BACKEND_URLS.hybrid = 'http://order-service-hybrid:3000';
  BACKEND_URLS.mixed = 'http://order-service-mixed:3000';
}

/**
 * Process checkout
 * @param {Array} items - Cart items
 * @param {string} customerId - Customer ID
 * @param {string} paymentMethod - Payment method
 * @param {string} variant - Backend variant (apm, otel, hybrid)
 */
export async function processCheckout(items, customerId, paymentMethod, variant = 'apm') {
  const baseUrl = BACKEND_URLS[variant] || BACKEND_URLS.apm;

  try {
    console.log(`[API] Processing checkout with ${variant} variant:`, baseUrl);

    const response = await axios.post(`${baseUrl}/checkout`, {
      items,
      customerId,
      paymentMethod
    }, {
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json'
      }
    });

    console.log('[API] Checkout successful:', response.data);
    return response.data;
  } catch (error) {
    console.error('[API] Checkout failed:', error);

    // Handle different error scenarios
    if (error.response) {
      // Server responded with error status
      throw new Error(error.response.data.message || error.response.data.error || 'Checkout failed');
    } else if (error.request) {
      // Request made but no response
      throw new Error('Backend service is not responding. Please try again.');
    } else {
      // Something else went wrong
      throw new Error('An unexpected error occurred');
    }
  }
}

/**
 * Check health of a specific backend variant
 */
export async function checkHealth(variant = 'apm') {
  const baseUrl = BACKEND_URLS[variant] || BACKEND_URLS.apm;

  try {
    const response = await axios.get(`${baseUrl}/health`, {
      timeout: 3000
    });
    return response.data;
  } catch (error) {
    console.error(`[API] Health check failed for ${variant}:`, error);
    return { status: 'unhealthy', variant };
  }
}

/**
 * Get available backend variants
 */
export function getAvailableVariants() {
  return [
    { value: 'apm', label: 'APM - New Relic Native', description: 'New Relic APM agent' },
    { value: 'otel', label: 'OTel - OpenTelemetry', description: 'OpenTelemetry SDK' },
    { value: 'hybrid', label: 'Hybrid - APM + OTel API', description: 'New Relic with OTel bridge' },
    { value: 'mixed', label: 'Mixed-Mode - Cross-variant Stack', description: 'Order(Hybrid) + Inventory(APM) + Payment(OTel)' }
  ];
}
