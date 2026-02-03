/**
 * OpenTelemetry Instrumentation for Payment Service
 */
'use strict';

const { NodeSDK } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-http');
const { OTLPMetricExporter } = require('@opentelemetry/exporter-metrics-otlp-http');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');
const { BatchSpanProcessor } = require('@opentelemetry/sdk-trace-node');
const { PeriodicExportingMetricReader } = require('@opentelemetry/sdk-metrics');

// Determine OTLP endpoints based on region
const region = (process.env.NEW_RELIC_REGION || 'US').toUpperCase();
const otlpEndpoints = {
  US: {
    traces: 'https://otlp.nr-data.net/v1/traces',
    metrics: 'https://otlp.nr-data.net/v1/metrics'
  },
  EU: {
    traces: 'https://otlp.eu01.nr-data.net/v1/traces',
    metrics: 'https://otlp.eu01.nr-data.net/v1/metrics'
  }
};
const endpoints = otlpEndpoints[region] || otlpEndpoints.US;

console.log(`OpenTelemetry configured for region: ${region}`);
console.log(`  Traces: ${endpoints.traces}`);
console.log(`  Metrics: ${endpoints.metrics}`);

// Configure OTLP trace exporter for New Relic
const traceExporter = new OTLPTraceExporter({
  url: endpoints.traces,
  headers: {
    'api-key': process.env.NEW_RELIC_LICENSE_KEY
  },
  timeoutMillis: 15000
});

// Add error logging for trace export failures
const originalTraceExport = traceExporter.export.bind(traceExporter);
traceExporter.export = function(spans, resultCallback) {
  console.log(`[OTel Traces] Exporting ${spans.length} span(s)`);
  originalTraceExport(spans, (result) => {
    if (result.code !== 0) {
      console.error('[OTel Traces] Export failed:', result.error || 'Unknown error');
    } else {
      console.log('[OTel Traces] Export successful');
    }
    resultCallback(result);
  });
};

// Configure OTLP metric exporter for New Relic
const metricExporter = new OTLPMetricExporter({
  url: endpoints.metrics,
  headers: {
    'api-key': process.env.NEW_RELIC_LICENSE_KEY
  },
  timeoutMillis: 15000
});

// Add error logging for metric export failures
const originalMetricExport = metricExporter.export.bind(metricExporter);
metricExporter.export = function(metrics, resultCallback) {
  console.log(`[OTel Metrics] Exporting metrics`);
  originalMetricExport(metrics, (result) => {
    if (result.code !== 0) {
      console.error('[OTel Metrics] Export failed:', result.error || 'Unknown error');
    } else {
      console.log('[OTel Metrics] Export successful');
    }
    resultCallback(result);
  });
};

// Create resource with service information
const resource = new Resource({
  [SemanticResourceAttributes.SERVICE_NAME]: process.env.NEW_RELIC_APP_NAME || 'NRDEMO Payment Service (OTel)',
  [SemanticResourceAttributes.SERVICE_VERSION]: '1.0.0',
  [SemanticResourceAttributes.SERVICE_INSTANCE_ID]: `${process.env.NEW_RELIC_APP_NAME || 'payment-service'}-${require('os').hostname()}`,
  'telemetry.sdk.language': 'nodejs'
});

// Create batch span processor for better performance
const spanProcessor = new BatchSpanProcessor(traceExporter, {
  maxQueueSize: 100,
  maxExportBatchSize: 10,
  scheduledDelayMillis: 1000 // Export every 1 second for demo responsiveness
});

// Create metric reader for periodic export
const metricReader = new PeriodicExportingMetricReader({
  exporter: metricExporter,
  exportIntervalMillis: 60000, // Export every 60 seconds
  exportTimeoutMillis: 30000 // 30 second timeout (must be <= interval)
});

// Initialize OpenTelemetry SDK with traces and metrics
const sdk = new NodeSDK({
  resource,
  spanProcessor,
  metricReader,
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-fs': {
        enabled: false // Reduce noise
      },
      '@opentelemetry/instrumentation-http': {
        enabled: true
      },
      '@opentelemetry/instrumentation-express': {
        enabled: true
      }
    })
  ]
});

// Start the SDK
sdk.start();
console.log('OpenTelemetry initialized for:', resource.attributes[SemanticResourceAttributes.SERVICE_NAME]);

// Graceful shutdown
process.on('SIGTERM', async () => {
  try {
    await sdk.shutdown();
    console.log('OpenTelemetry SDK shut down successfully');
  } catch (err) {
    console.error('Error shutting down OpenTelemetry SDK:', err);
  } finally {
    process.exit(0);
  }
});

module.exports = sdk;
