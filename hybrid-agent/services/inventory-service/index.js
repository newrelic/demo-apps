/**
 * Inventory Service - Stock management with PostgreSQL
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
const inventoryRouter = require('./routes/inventory');

const app = express();
const port = process.env.PORT || 4000;

// Create service logger
const logger = createLogger('inventory-service', variant);

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
    service: 'inventory-service',
    variant,
    status: 'healthy',
    timestamp: new Date().toISOString()
  });
});

// Routes
app.use('/', inventoryRouter);

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error({ error: err.message, stack: err.stack }, 'Unhandled error');

  res.status(500).json({
    error: 'Internal server error',
    message: err.message
  });
});

// Graceful shutdown
process.on('SIGTERM', async () => {
  logger.info('SIGTERM received, shutting down gracefully');
  const db = require('./shared/db');
  await db.close();
  process.exit(0);
});

// Start server
app.listen(port, () => {
  logger.info({ port, variant }, `Inventory Service started`);
  console.log(`Inventory Service (${variant}) listening on port ${port}`);
});
