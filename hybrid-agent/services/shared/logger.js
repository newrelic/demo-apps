const pino = require('pino');
const { trace, context } = require('@opentelemetry/api');

/**
 * Creates a Pino logger with trace context support for APM, OTel, and Hybrid modes
 *
 * Automatically detects instrumentation type and adds appropriate trace metadata
 * - APM: Uses newrelic.getLinkingMetadata()
 * - OTel: Uses @opentelemetry/api to extract trace/span IDs
 * - Hybrid: Uses New Relic's built-in OTel bridge
 */
function createLogger(serviceName, instrumentationType = 'apm') {
  const logger = pino({
    name: serviceName,
    level: process.env.LOG_LEVEL || 'info',
    formatters: {
      level(label) {
        return { level: label };
      }
    },
    mixin() {
      const mixinData = {};

      try {
        // For APM mode: Use New Relic's linking metadata
        // For Hybrid mode: Use New Relic's linking metadata (agent bridges OTel data)
        if ((instrumentationType === 'apm' || instrumentationType === 'hybrid')) {
          if (typeof require !== 'undefined') {
            try {
              const newrelic = require('newrelic');
              const linkingMetadata = newrelic.getLinkingMetadata();
              Object.assign(mixinData, linkingMetadata);
            } catch (err) {
              // New Relic not available, continue
            }
          }
        }

        // For OTel mode (or as fallback for hybrid), use OpenTelemetry API
        if (instrumentationType === 'otel') {
          const span = trace.getSpan(context.active());
          if (span) {
            const spanContext = span.spanContext();
            mixinData['trace.id'] = spanContext.traceId;
            mixinData['span.id'] = spanContext.spanId;
            mixinData['trace.flags'] = spanContext.traceFlags;
          }
        }
      } catch (err) {
        // Fail silently - logging should never break the app
      }

      return mixinData;
    }
  });

  return logger;
}

/**
 * Express middleware to add request-scoped logger
 */
function requestLoggerMiddleware(logger) {
  return (req, res, next) => {
    const startTime = Date.now();

    // Log incoming request
    logger.info({
      method: req.method,
      url: req.url,
      headers: req.headers,
      query: req.query
    }, 'Incoming request');

    // Log response when finished
    res.on('finish', () => {
      const duration = Date.now() - startTime;
      logger.info({
        method: req.method,
        url: req.url,
        statusCode: res.statusCode,
        duration
      }, 'Request completed');
    });

    next();
  };
}

module.exports = {
  createLogger,
  requestLoggerMiddleware
};
