import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

// Check if Browser agent is initialized
if (!window.NREUM || !window.NREUM.init) {
  console.log('[Storefront] Running without Browser monitoring - backend instrumentation only');
} else {
  console.log('[Storefront] Browser monitoring enabled');
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
