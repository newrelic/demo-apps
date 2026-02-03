/**
 * Hybrid Instrumentation (New Relic with OpenTelemetry Bridge)
 *
 * This demonstrates the simplified hybrid approach:
 * 1. Load the New Relic agent (reads config from newrelic.js)
 * 2. Agent auto-instruments with OpenTelemetry bridge
 * 3. Application uses @opentelemetry/api for custom instrumentation
 *
 * Reference: https://github.com/newrelic/newrelic-node-examples/tree/main/opentelemetry-example
 *
 * Data Flow: Application → New Relic Agent (OTel bridge) → collector.newrelic.com
 */
'use strict';

// Load New Relic agent (with opentelemetry.enabled: true in newrelic.js)
const newrelic = require('newrelic');

console.log('=== HYBRID MODE: New Relic with OpenTelemetry Bridge ===');
console.log('New Relic agent loaded with OTel bridge enabled');
console.log('Data destination: collector.newrelic.com');

module.exports = newrelic;
