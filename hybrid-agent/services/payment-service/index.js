/**
 * Payment Service - Payment processing with simulated delays/errors
 * Supports APM, OTel, and Hybrid instrumentation modes
 */
'use strict';

// Initialize telemetry first
const variant = process.env.VARIANT || 'apm';
let telemetry;

if (variant === 'apm') {
  telemetry = require('./telemetry/apm');
} else if (variant === 'otel') {
  telemetry = require('./telemetry/otel');
} else if (variant === 'hybrid') {
  telemetry = require('./telemetry/hybrid');
}

const express = require('express');
const { createLogger, requestLoggerMiddleware } = require('./shared/logger');
const paymentRouter = require('./routes/payment');

const app = express();
const port = process.env.PORT || 5000;

// Create service logger
const logger = createLogger('payment-service', variant);

// Middleware
app.use(express.json());

// CORS middleware for browser requests
app.use((req, res, next) => {
  res.header('Access-Control-Allow-Origin', '*');
  res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
  res.header('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    return res.sendStatus(200);
  }

  next();
});

app.use(requestLoggerMiddleware(logger));

// Add logger to request object
app.use((req, res, next) => {
  req.logger = logger;
  next();
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    service: 'payment-service',
    variant,
    status: 'healthy',
    timestamp: new Date().toISOString()
  });
});

// Routes
app.use('/', paymentRouter);

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error({ error: err.message, stack: err.stack }, 'Unhandled error');

  res.status(500).json({
    error: 'Internal server error',
    message: err.message
  });
});

// Graceful shutdown
process.on('SIGTERM', () => {
  logger.info('SIGTERM received, shutting down gracefully');
  process.exit(0);
});

// Start server
app.listen(port, () => {
  logger.info({ port, variant }, `Payment Service started`);
  console.log(`Payment Service (${variant}) listening on port ${port}`);
});
