'use strict';

/**
 * New Relic agent configuration
 *
 * OpenTelemetry bridge behavior by variant:
 * - APM: opentelemetry.enabled = false (native New Relic instrumentation)
 * - Hybrid: opentelemetry.enabled = true (New Relic with OTel bridge)
 * - OTel: This file is not used (pure OpenTelemetry SDK)
 *
 * When opentelemetry.enabled is true:
 * - The agent automatically uses OpenTelemetry-compatible instrumentation
 * - Custom instrumentation should use @opentelemetry/api
 */
exports.config = {
  logging: {
    level: process.env.NEW_RELIC_LOG_LEVEL || 'info'
  },

  // Enable OpenTelemetry bridge ONLY for hybrid variant
  opentelemetry: {
    enabled: process.env.VARIANT === 'hybrid',
    traces: {
      enabled: process.env.VARIANT === 'hybrid'
    },
    metrics: {
      enabled: process.env.VARIANT === 'hybrid'
    }
  },

  distributed_tracing: {
    enabled: true
  },

  application_logging: {
    enabled: true,
    forwarding: {
      enabled: true,
      max_samples_stored: 10000
    },
    metrics: {
      enabled: true
    },
    local_decorating: {
      enabled: true
    }
  },

  allow_all_headers: true,

  attributes: {
    exclude: [
      'request.headers.cookie',
      'request.headers.authorization',
      'request.headers.proxyAuthorization',
      'request.headers.setCookie*',
      'request.headers.x*',
      'response.headers.cookie',
      'response.headers.authorization',
      'response.headers.proxyAuthorization',
      'response.headers.setCookie*',
      'response.headers.x*'
    ]
  }
};
