import React from 'react';
import './ProductCatalog.css';

// Product catalog matching the database seed data
const PRODUCTS = [
  {
    sku: 'LAPTOP-001',
    name: 'Gaming Laptop',
    price: 1299.99,
    description: 'High-performance gaming laptop with RTX graphics',
    available: 5
  },
  {
    sku: 'MOUSE-001',
    name: 'Wireless Mouse',
    price: 29.99,
    description: 'Ergonomic wireless mouse with precision tracking',
    available: 50
  },
  {
    sku: 'MONITOR-001',
    name: '4K Monitor',
    price: 399.99,
    description: '27-inch 4K UHD monitor with HDR support',
    available: 3
  },
  {
    sku: 'KEYBOARD-001',
    name: 'Mechanical Keyboard',
    price: 129.99,
    description: 'RGB mechanical keyboard with cherry switches',
    available: 15
  },
  {
    sku: 'HEADSET-001',
    name: 'Gaming Headset',
    price: 149.99,
    description: '7.1 surround sound gaming headset',
    available: 0 // Out of stock for demo
  }
];

function ProductCatalog({ onAddToCart }) {
  return (
    <div className="product-catalog">
      <h2>Products</h2>
      <div className="product-grid">
        {PRODUCTS.map(product => (
          <div key={product.sku} className="product-card">
            <div className="product-info">
              <h3 className="product-name">{product.name}</h3>
              <p className="product-description">{product.description}</p>
              <p className="product-price">${product.price.toFixed(2)}</p>
              <p className={`product-stock ${product.available === 0 ? 'out-of-stock' : ''}`}>
                {product.available > 0 ? `${product.available} in stock` : 'Out of stock'}
              </p>
            </div>
            <button
              className="add-to-cart-btn"
              onClick={() => onAddToCart(product)}
              disabled={product.available === 0}
              id={`add-to-cart-${product.sku}`}
            >
              {product.available > 0 ? 'Add to Cart' : 'Out of Stock'}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default ProductCatalog;
