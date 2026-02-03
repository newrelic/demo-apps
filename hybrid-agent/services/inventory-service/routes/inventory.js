const express = require('express');
const { v4: uuidv4 } = require('uuid');
const db = require('../shared/db');

const router = express.Router();

/**
 * GET /inventory/:sku
 * Get inventory information for a specific product
 */
router.get('/inventory/:sku', async (req, res) => {
  const { sku } = req.params;
  const logger = req.logger || console;

  logger.info({ sku }, 'Checking inventory');

  try {
    const result = await db.query(
      'SELECT sku, name, price, available, reserved FROM products WHERE sku = $1',
      [sku]
    );

    if (result.rows.length === 0) {
      logger.warn({ sku }, 'Product not found');
      return res.status(404).json({
        error: 'Product not found',
        sku
      });
    }

    const product = result.rows[0];

    // Add custom attributes based on variant
    if (process.env.VARIANT === 'apm') {
      try {
        const newrelic = require('newrelic');
        newrelic.addCustomSpanAttributes({
          'inventory.sku': sku,
          'inventory.available': product.available,
          'inventory.reserved': product.reserved,
          'service.variant': process.env.VARIANT
        });
      } catch (err) {
        // New Relic not available
      }
    } else if (process.env.VARIANT === 'hybrid' || process.env.VARIANT === 'otel') {
      try {
        const { trace } = require('@opentelemetry/api');
        const span = trace.getActiveSpan();
        if (span) {
          span.setAttributes({
            'inventory.sku': sku,
            'inventory.available': product.available,
            'inventory.reserved': product.reserved,
            'service.variant': process.env.VARIANT
          });
        }
      } catch (err) {
        // OpenTelemetry API not available
      }
    }

    logger.info({ sku, available: product.available }, 'Inventory checked');

    res.json({
      sku: product.sku,
      name: product.name,
      price: parseFloat(product.price),
      available: product.available,
      reserved: product.reserved,
      inStock: product.available > 0
    });

  } catch (err) {
    logger.error({ sku, error: err.message }, 'Error checking inventory');
    res.status(500).json({
      error: 'Failed to check inventory',
      message: err.message
    });
  }
});

/**
 * POST /reserve
 * Reserve inventory for an order
 */
router.post('/reserve', async (req, res) => {
  const { items, orderId } = req.body;
  const reservationId = uuidv4();
  const logger = req.logger || console;

  logger.info({ orderId, reservationId, itemCount: items?.length }, 'Starting inventory reservation');

  try {
    // Validate request
    if (!items || !Array.isArray(items) || items.length === 0) {
      logger.warn({ orderId }, 'Invalid reservation request: no items');
      return res.status(400).json({
        error: 'Invalid request',
        message: 'Items array is required'
      });
    }

    if (!orderId) {
      logger.warn({ reservationId }, 'Invalid reservation request: no orderId');
      return res.status(400).json({
        error: 'Invalid request',
        message: 'Order ID is required'
      });
    }

    // Get a database client for transaction
    const client = await db.getClient();

    try {
      await client.query('BEGIN');

      // Check availability for all items
      const unavailableItems = [];
      for (const item of items) {
        const result = await client.query(
          'SELECT sku, name, available FROM products WHERE sku = $1 FOR UPDATE',
          [item.sku]
        );

        if (result.rows.length === 0) {
          unavailableItems.push({
            sku: item.sku,
            reason: 'Product not found'
          });
          continue;
        }

        const product = result.rows[0];
        if (product.available < item.quantity) {
          unavailableItems.push({
            sku: item.sku,
            name: product.name,
            requested: item.quantity,
            available: product.available,
            reason: 'Insufficient stock'
          });
        }
      }

      // If any items are unavailable, rollback and return error
      if (unavailableItems.length > 0) {
        await client.query('ROLLBACK');

        logger.warn({ orderId, reservationId, unavailableItems }, 'Reservation failed: items unavailable');

        return res.status(409).json({
          error: 'Insufficient inventory',
          message: 'One or more items are out of stock',
          unavailableItems,
          reservationId
        });
      }

      // Reserve all items
      for (const item of items) {
        await client.query(
          'UPDATE products SET available = available - $1, reserved = reserved + $1 WHERE sku = $2',
          [item.quantity, item.sku]
        );

        logger.info({ sku: item.sku, quantity: item.quantity }, 'Inventory reserved');
      }

      await client.query('COMMIT');

      logger.info({ orderId, reservationId, itemCount: items.length }, 'Reservation completed successfully');

      // Add custom attributes based on variant
      if (process.env.VARIANT === 'apm') {
        try {
          const newrelic = require('newrelic');
          newrelic.addCustomSpanAttributes({
            'inventory.reservation_id': reservationId,
            'order.id': orderId,
            'order.item_count': items.length,
            'service.variant': process.env.VARIANT
          });
        } catch (err) {
          // New Relic not available
        }
      } else if (process.env.VARIANT === 'hybrid' || process.env.VARIANT === 'otel') {
        try {
          const { trace } = require('@opentelemetry/api');
          const span = trace.getActiveSpan();
          if (span) {
            span.setAttributes({
              'inventory.reservation_id': reservationId,
              'order.id': orderId,
              'order.item_count': items.length,
              'service.variant': process.env.VARIANT
            });
          }
        } catch (err) {
          // OpenTelemetry API not available
        }
      }

      res.status(201).json({
        reservationId,
        status: 'reserved',
        orderId,
        items: items.map(item => ({
          sku: item.sku,
          quantity: item.quantity
        })),
        timestamp: new Date().toISOString()
      });

    } catch (err) {
      await client.query('ROLLBACK');
      throw err;
    } finally {
      client.release();
    }

  } catch (err) {
    logger.error({ orderId, reservationId, error: err.message }, 'Reservation failed');
    res.status(500).json({
      error: 'Reservation failed',
      message: 'An unexpected error occurred',
      reservationId
    });
  }
});

module.exports = router;
