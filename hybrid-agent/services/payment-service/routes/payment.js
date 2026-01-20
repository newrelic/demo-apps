const express = require('express');
const { v4: uuidv4 } = require('uuid');

const router = express.Router();

/**
 * Simulate payment gateway processing
 * Includes configurable delay and error rate for demo purposes
 */
async function simulatePaymentGateway(amount, orderId, logger) {
  const delayMs = parseInt(process.env.PAYMENT_DELAY_MS) || 2000;
  const errorRate = parseFloat(process.env.PAYMENT_ERROR_RATE) || 0.1;

  logger.info({ orderId, delayMs }, 'Simulating payment gateway processing');

  // Simulate processing delay
  await new Promise(resolve => setTimeout(resolve, delayMs));

  // Simulate random errors
  if (Math.random() < errorRate) {
    throw new Error('Payment gateway declined transaction');
  }

  return {
    approved: true,
    processingTime: delayMs
  };
}

/**
 * POST /process-payment
 * Process a payment for an order
 *
 * Demonstrates:
 * - Intentional bottleneck (2s delay) for distributed tracing demos
 * - Random errors for error tracking demos
 * - Custom instrumentation for business logic
 */
router.post('/process-payment', async (req, res) => {
  const { amount, orderId, paymentMethod } = req.body;
  const transactionId = uuidv4();
  const logger = req.logger || console;
  const startTime = Date.now();

  logger.info({ orderId, transactionId, amount, paymentMethod }, 'Starting payment processing');

  try {
    // Validate request
    if (!amount || !orderId || !paymentMethod) {
      logger.warn({ orderId, transactionId }, 'Invalid payment request');
      return res.status(400).json({
        error: 'Invalid request',
        message: 'Amount, order ID, and payment method are required'
      });
    }

    if (amount <= 0) {
      logger.warn({ orderId, transactionId, amount }, 'Invalid payment amount');
      return res.status(400).json({
        error: 'Invalid amount',
        message: 'Payment amount must be greater than zero'
      });
    }

    // Custom instrumentation for APM mode (custom segment)
    if (process.env.VARIANT === 'apm') {
      try {
        const newrelic = require('newrelic');

        // Create custom segment for payment gateway call
        await newrelic.startSegment('PaymentGateway/ProcessPayment', true, async () => {
          await simulatePaymentGateway(amount, orderId, logger);
        });
      } catch (err) {
        // New Relic not available, fall back to regular processing
        await simulatePaymentGateway(amount, orderId, logger);
      }
    } else {
      // For Hybrid/OTel modes, process normally (auto-instrumentation handles it)
      await simulatePaymentGateway(amount, orderId, logger);
    }

    const processingTime = Date.now() - startTime;

    // Add custom attributes based on variant
    if (process.env.VARIANT === 'apm') {
      try {
        const newrelic = require('newrelic');
        newrelic.addCustomSpanAttributes({
          'payment.transaction_id': transactionId,
          'order.id': orderId,
          'payment.amount': amount,
          'payment.method': paymentMethod,
          'payment.processing_time': processingTime,
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
            'payment.transaction_id': transactionId,
            'order.id': orderId,
            'payment.amount': amount,
            'payment.method': paymentMethod,
            'payment.processing_time': processingTime,
            'service.variant': process.env.VARIANT
          });
        }
      } catch (err) {
        // OpenTelemetry API not available
      }
    }

    logger.info({
      orderId,
      transactionId,
      amount,
      processingTime,
      status: 'approved'
    }, 'Payment processed successfully');

    res.status(200).json({
      transactionId,
      status: 'approved',
      amount,
      orderId,
      paymentMethod,
      processingTime,
      timestamp: new Date().toISOString()
    });

  } catch (err) {
    const processingTime = Date.now() - startTime;

    logger.error({
      orderId,
      transactionId,
      error: err.message,
      processingTime
    }, 'Payment processing failed');

    // Record error based on variant
    if (process.env.VARIANT === 'apm') {
      try {
        const newrelic = require('newrelic');
        newrelic.noticeError(err, {
          'payment.transaction_id': transactionId,
          'order.id': orderId,
          'payment.amount': amount,
          'payment.method': paymentMethod,
          'service.variant': process.env.VARIANT
        });
      } catch (e) {
        // New Relic not available
      }
    } else if (process.env.VARIANT === 'hybrid' || process.env.VARIANT === 'otel') {
      try {
        const { trace } = require('@opentelemetry/api');
        const span = trace.getActiveSpan();
        if (span) {
          span.recordException(err);
          span.setAttributes({
            'payment.transaction_id': transactionId,
            'order.id': orderId,
            'payment.amount': amount,
            'payment.method': paymentMethod,
            'service.variant': process.env.VARIANT
          });
        }
      } catch (e) {
        // OpenTelemetry API not available
      }
    }

    res.status(402).json({
      transactionId,
      status: 'declined',
      error: 'Payment failed',
      message: err.message,
      orderId,
      processingTime,
      timestamp: new Date().toISOString()
    });
  }
});

module.exports = router;
