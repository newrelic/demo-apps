import React, { useState } from 'react';
import ProductCatalog from './components/ProductCatalog';
import ShoppingCart from './components/ShoppingCart';
import CheckoutForm from './components/CheckoutForm';
import './App.css';

function App() {
  const [cart, setCart] = useState([]);
  const [selectedVariant, setSelectedVariant] = useState('apm');
  const [showCheckout, setShowCheckout] = useState(false);
  const [orderResult, setOrderResult] = useState(null);

  const addToCart = (product) => {
    setCart(prevCart => {
      const existingItem = prevCart.find(item => item.sku === product.sku);

      if (existingItem) {
        return prevCart.map(item =>
          item.sku === product.sku
            ? { ...item, quantity: item.quantity + 1 }
            : item
        );
      }

      return [...prevCart, { ...product, quantity: 1 }];
    });
  };

  const removeFromCart = (sku) => {
    setCart(prevCart => prevCart.filter(item => item.sku !== sku));
  };

  const updateQuantity = (sku, quantity) => {
    if (quantity <= 0) {
      removeFromCart(sku);
      return;
    }

    setCart(prevCart =>
      prevCart.map(item =>
        item.sku === sku ? { ...item, quantity } : item
      )
    );
  };

  const getTotalAmount = () => {
    return cart.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  };

  const handleCheckoutComplete = (result) => {
    setOrderResult(result);
    setCart([]);
    setShowCheckout(false);

    // Show success message for a few seconds
    setTimeout(() => {
      setOrderResult(null);
    }, 5000);
  };

  const handleCheckoutError = (error) => {
    setOrderResult({ error: true, message: error.message });

    // Show error message for a few seconds
    setTimeout(() => {
      setOrderResult(null);
    }, 5000);
  };

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <h1>Hybrid Agent Demo Store</h1>
          <p className="subtitle">Compare APM, OTel, and Hybrid Observability</p>
        </div>

        <div className="variant-selector">
          <label htmlFor="variant-select">Backend Variant:</label>
          <select
            id="variant-select"
            value={selectedVariant}
            onChange={(e) => setSelectedVariant(e.target.value)}
            className="variant-dropdown"
          >
            <option value="apm">APM - New Relic Native</option>
            <option value="otel">OTel - OpenTelemetry</option>
            <option value="hybrid">Hybrid - APM + OTel API</option>
            <option value="mixed">Mixed-Mode - Cross-variant Stack</option>
          </select>
        </div>
      </header>

      {orderResult && (
        <div className={`notification ${orderResult.error ? 'notification-error' : 'notification-success'}`}>
          {orderResult.error ? (
            <>
              <strong>Order Failed!</strong> {orderResult.message}
            </>
          ) : (
            <>
              <strong>Order Successful!</strong> Order ID: {orderResult.orderId}
              <br />
              Transaction ID: {orderResult.transactionId}
            </>
          )}
        </div>
      )}

      <main className="main-content">
        {!showCheckout ? (
          <>
            <ProductCatalog onAddToCart={addToCart} />
            <ShoppingCart
              cart={cart}
              onRemove={removeFromCart}
              onUpdateQuantity={updateQuantity}
              onCheckout={() => setShowCheckout(true)}
            />
          </>
        ) : (
          <CheckoutForm
            cart={cart}
            variant={selectedVariant}
            totalAmount={getTotalAmount()}
            onComplete={handleCheckoutComplete}
            onError={handleCheckoutError}
            onCancel={() => setShowCheckout(false)}
          />
        )}
      </main>

      <footer className="footer">
        <p>Demo application for observability comparison - Not for production use</p>
      </footer>
    </div>
  );
}

export default App;
