import React, { useState } from 'react';
import { processCheckout } from '../services/api';
import './CheckoutForm.css';

function CheckoutForm({ cart, variant, totalAmount, onComplete, onError, onCancel }) {
  const [customerId, setCustomerId] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('credit-card');
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!customerId.trim()) {
      alert('Please enter a customer ID');
      return;
    }

    setIsProcessing(true);

    try {
      // Process checkout through selected backend variant
      const result = await processCheckout(
        cart.map(item => ({
          sku: item.sku,
          name: item.name,
          price: item.price,
          quantity: item.quantity
        })),
        customerId,
        paymentMethod,
        variant
      );

      console.log('[Checkout] Order completed:', result);
      onComplete(result);
    } catch (error) {
      console.error('[Checkout] Order failed:', error);
      onError(error);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="checkout-form-container">
      <h2>Checkout</h2>

      <div className="checkout-info">
        <p>Processing via: <strong>{variant.toUpperCase()}</strong> backend</p>
        <p>Total Amount: <strong>${totalAmount.toFixed(2)}</strong></p>
      </div>

      <form onSubmit={handleSubmit} className="checkout-form">
        <div className="form-group">
          <label htmlFor="customer-id">Customer ID</label>
          <input
            type="text"
            id="customer-id"
            value={customerId}
            onChange={(e) => setCustomerId(e.target.value)}
            placeholder="Enter your customer ID (e.g., CUST-001)"
            disabled={isProcessing}
            required
          />
        </div>

        <div className="form-group">
          <label htmlFor="payment-method">Payment Method</label>
          <select
            id="payment-method"
            value={paymentMethod}
            onChange={(e) => setPaymentMethod(e.target.value)}
            disabled={isProcessing}
          >
            <option value="credit-card">Credit Card</option>
            <option value="debit-card">Debit Card</option>
            <option value="paypal">PayPal</option>
            <option value="bank-transfer">Bank Transfer</option>
          </select>
        </div>

        <div className="order-summary">
          <h3>Order Summary</h3>
          <div className="summary-items">
            {cart.map(item => (
              <div key={item.sku} className="summary-item">
                <span>{item.name} x {item.quantity}</span>
                <span>${(item.price * item.quantity).toFixed(2)}</span>
              </div>
            ))}
          </div>
          <div className="summary-total">
            <span>Total:</span>
            <span>${totalAmount.toFixed(2)}</span>
          </div>
        </div>

        <div className="form-actions">
          <button
            type="button"
            onClick={onCancel}
            className="cancel-btn"
            disabled={isProcessing}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="submit-btn"
            id="complete-order"
            disabled={isProcessing}
          >
            {isProcessing ? (
              <>
                <span className="spinner"></span>
                Processing...
              </>
            ) : (
              'Complete Order'
            )}
          </button>
        </div>
      </form>

      {isProcessing && (
        <div className="processing-note">
          <p>
            Note: Payment processing includes a 2-second delay to demonstrate
            distributed tracing bottleneck detection.
          </p>
        </div>
      )}
    </div>
  );
}

export default CheckoutForm;
