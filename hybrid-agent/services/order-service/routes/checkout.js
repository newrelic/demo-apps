const express = require('express');
const axios = require('axios');
const { v4: uuidv4 } = require('uuid');
const db = require('../shared/db');

const router = express.Router();

/**
 * POST /checkout
 * Process a customer order through the checkout flow
 *
 * Flow:
 * 1. Validate cart items
 * 2. Check inventory availability
 * 3. Reserve inventory
 * 4. Process payment
 * 5. Create order record
 */
router.post('/checkout', async (req, res) => {
  const { items, customerId, paymentMethod } = req.body;
  const orderId = uuidv4();
  const logger = req.logger || console;

  logger.info({ orderId, customerId, itemCount: items?.length }, 'Starting checkout');

  try {
    // Validate request
    if (!items || !Array.isArray(items) || items.length === 0) {
      logger.warn({ orderId }, 'Invalid checkout request: no items');
      return res.status(400).json({
        error: 'Invalid request',
        message: 'Cart must contain at least one item'
      });
    }

    if (!customerId || !paymentMethod) {
      logger.warn({ orderId }, 'Invalid checkout request: missing customer or payment info');
      return res.status(400).json({
        error: 'Invalid request',
        message: 'Customer ID and payment method are required'
      });
    }

    // Calculate total
    const totalAmount = items.reduce((sum, item) => {
      return sum + (parseFloat(item.price) * parseInt(item.quantity));
    }, 0);

    logger.info({ orderId, totalAmount }, 'Calculated order total');

    // Get inventory service URL based on variant
    const inventoryHost = process.env.INVENTORY_SERVICE_HOST ||
                         `inventory-service-${process.env.VARIANT || 'apm'}`;
    const inventoryPort = process.env.INVENTORY_SERVICE_PORT || 4000;
    const inventoryUrl = `http://${inventoryHost}:${inventoryPort}`;

    // Reserve inventory
    logger.info({ orderId, inventoryUrl }, 'Reserving inventory');
    let reservationResponse;
    try {
      reservationResponse = await axios.post(`${inventoryUrl}/reserve`, {
        items: items.map(item => ({
          sku: item.sku,
          quantity: item.quantity
        })),
        orderId
      });
    } catch (err) {
      logger.error({ orderId, error: err.message }, 'Inventory reservation failed');

      if (err.response?.status === 409) {
        return res.status(409).json({
          error: 'Out of stock',
          message: err.response.data.message || 'One or more items are out of stock',
          orderId
        });
      }

      return res.status(502).json({
        error: 'Inventory service error',
        message: 'Could not check inventory availability',
        orderId
      });
    }

    logger.info({ orderId, reservationId: reservationResponse.data.reservationId }, 'Inventory reserved');

    // Get payment service URL based on variant
    const paymentHost = process.env.PAYMENT_SERVICE_HOST ||
                       `payment-service-${process.env.VARIANT || 'apm'}`;
    const paymentPort = process.env.PAYMENT_SERVICE_PORT || 5000;
    const paymentUrl = `http://${paymentHost}:${paymentPort}`;

    // Process payment
    logger.info({ orderId, paymentUrl, amount: totalAmount }, 'Processing payment');
    let paymentResponse;
    try {
      paymentResponse = await axios.post(`${paymentUrl}/process-payment`, {
        amount: totalAmount,
        orderId,
        paymentMethod
      });
    } catch (err) {
      logger.error({ orderId, error: err.message }, 'Payment processing failed');

      // TODO: Release inventory reservation on payment failure
      return res.status(502).json({
        error: 'Payment failed',
        message: err.response?.data?.message || 'Payment could not be processed',
        orderId
      });
    }

    logger.info({
      orderId,
      transactionId: paymentResponse.data.transactionId,
      processingTime: paymentResponse.data.processingTime
    }, 'Payment processed successfully');

    // Create order record
    const variant = process.env.VARIANT || 'apm';
    await db.query(
      'INSERT INTO orders (order_id, customer_id, total_amount, status, variant) VALUES ($1, $2, $3, $4, $5)',
      [orderId, customerId, totalAmount, 'completed', variant]
    );

    // Create order items records
    for (const item of items) {
      await db.query(
        'INSERT INTO order_items (order_id, sku, quantity, price) VALUES ($1, $2, $3, $4)',
        [orderId, item.sku, item.quantity, item.price]
      );
    }

    logger.info({ orderId, status: 'completed' }, 'Order completed successfully');

    // Add custom attributes based on variant
    if (process.env.VARIANT === 'apm') {
      try {
        const newrelic = require('newrelic');
        newrelic.addCustomSpanAttributes({
          'order.id': orderId,
          'customer.id': customerId,
          'order.item_count': items.length,
          'order.total_amount': totalAmount,
          'service.variant': variant,
          'payment.method': paymentMethod
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
            'order.id': orderId,
            'customer.id': customerId,
            'order.item_count': items.length,
            'order.total_amount': totalAmount,
            'service.variant': variant,
            'payment.method': paymentMethod
          });
        }
      } catch (err) {
        // OpenTelemetry API not available
      }
    }

    res.status(201).json({
      orderId,
      status: 'completed',
      totalAmount,
      transactionId: paymentResponse.data.transactionId,
      reservationId: reservationResponse.data.reservationId,
      timestamp: new Date().toISOString()
    });

  } catch (err) {
    logger.error({ orderId, error: err.message, stack: err.stack }, 'Checkout failed');

    res.status(500).json({
      error: 'Checkout failed',
      message: 'An unexpected error occurred',
      orderId
    });
  }
});

module.exports = router;
