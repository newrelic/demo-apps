import React from 'react';
import './ShoppingCart.css';

function ShoppingCart({ cart, onRemove, onUpdateQuantity, onCheckout }) {
  const getTotalAmount = () => {
    return cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  };

  const getTotalItems = () => {
    return cart.reduce((sum, item) => sum + item.quantity, 0);
  };

  if (cart.length === 0) {
    return (
      <div className="shopping-cart empty">
        <h2>Shopping Cart</h2>
        <p className="empty-cart-message">Your cart is empty</p>
      </div>
    );
  }

  return (
    <div className="shopping-cart">
      <h2>Shopping Cart ({getTotalItems()} items)</h2>

      <div className="cart-items">
        {cart.map(item => (
          <div key={item.sku} className="cart-item">
            <div className="cart-item-info">
              <h3>{item.name}</h3>
              <p className="cart-item-price">${item.price.toFixed(2)} each</p>
            </div>

            <div className="cart-item-controls">
              <div className="quantity-controls">
                <button
                  onClick={() => onUpdateQuantity(item.sku, item.quantity - 1)}
                  className="quantity-btn"
                  aria-label="Decrease quantity"
                >
                  -
                </button>
                <span className="quantity-display">{item.quantity}</span>
                <button
                  onClick={() => onUpdateQuantity(item.sku, item.quantity + 1)}
                  className="quantity-btn"
                  aria-label="Increase quantity"
                >
                  +
                </button>
              </div>

              <p className="cart-item-subtotal">
                ${(item.price * item.quantity).toFixed(2)}
              </p>

              <button
                onClick={() => onRemove(item.sku)}
                className="remove-btn"
                aria-label="Remove item"
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="cart-summary">
        <div className="cart-total">
          <span>Total:</span>
          <span className="total-amount">${getTotalAmount().toFixed(2)}</span>
        </div>

        <button
          onClick={onCheckout}
          className="checkout-btn"
          id="proceed-to-checkout"
        >
          Proceed to Checkout
        </button>
      </div>
    </div>
  );
}

export default ShoppingCart;
