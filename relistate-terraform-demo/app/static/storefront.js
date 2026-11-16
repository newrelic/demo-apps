'use strict';
const $ = (selector) => document.querySelector(selector);
const productGrid = $('#productGrid');
const cartDrawer = $('#cartDrawer');
const overlay = $('#overlay');
const toastElement = $('#toast');
let catalog = [];
let activeFilter = 'All';
let cart = {};
try { cart = JSON.parse(localStorage.getItem('relistate-demo-cart') || '{}') || {}; }
catch (_error) { cart = {}; }
let toastTimeout;
const formatPrice = cents => new Intl.NumberFormat('en-US', {style:'currency', currency:'USD'}).format(cents / 100);
const saveCart = () => { localStorage.setItem('relistate-demo-cart', JSON.stringify(cart)); updateCart(); };
function toast(message) {
  toastElement.textContent = message;
  toastElement.classList.add('show');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => toastElement.classList.remove('show'), 2600);
}
async function getJSON(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}
function renderProducts() {
  const items = activeFilter === 'All' ? catalog : catalog.filter(item => item.category === activeFilter);
  productGrid.replaceChildren();
  for (const item of items) {
    const article = document.createElement('article');
    article.className = 'product-card';
    article.innerHTML = `<div class="product-visual ${item.color}"><span class="product-tag"></span><span class="product-emoji" aria-hidden="true"></span></div>
      <div class="product-meta"><h3></h3><strong></strong></div><p class="product-desc"></p><button class="add-to-cart" type="button">Add to bag +</button>`;
    article.querySelector('.product-tag').textContent = item.tag;
    article.querySelector('.product-emoji').textContent = item.emoji;
    article.querySelector('h3').textContent = item.name;
    article.querySelector('strong').textContent = formatPrice(item.price_cents);
    article.querySelector('.product-desc').textContent = item.description;
    article.querySelector('.add-to-cart').addEventListener('click', () => {
      cart[item.id] = Math.min((cart[item.id] || 0) + 1, 10);
      saveCart(); toast(`${item.name} added to your bag`);
    });
    productGrid.appendChild(article);
  }
}
function updateCart() {
  const lineItems = catalog.filter(item => (cart[item.id] || 0) > 0);
  $('#cartCount').textContent = lineItems.reduce((sum, item) => sum + cart[item.id], 0);
  const container = $('#cartItems');
  container.replaceChildren();
  let subtotal = 0;
  if (!lineItems.length) {
    const p = document.createElement('p'); p.className = 'loading'; p.textContent = 'Your bag is empty. Find something you love!'; container.appendChild(p);
  }
  for (const item of lineItems) {
    const qty = cart[item.id]; subtotal += item.price_cents * qty;
    const line = document.createElement('div'); line.className = 'cart-line';
    const desc = document.createElement('div'); desc.innerHTML = '<h3></h3><small></small>';
    desc.querySelector('h3').textContent = item.name;
    desc.querySelector('small').textContent = `${qty} × ${formatPrice(item.price_cents)}`;
    const remove = document.createElement('button'); remove.textContent = 'Remove'; remove.setAttribute('aria-label', `Remove ${item.name}`);
    remove.addEventListener('click', () => {delete cart[item.id]; saveCart();});
    line.append(desc,remove); container.appendChild(line);
  }
  $('#subtotal').textContent = formatPrice(subtotal);
  $('#checkoutButton').disabled = lineItems.length === 0;
}
function toggleCart(open) {
  overlay.hidden = !open;
  cartDrawer.classList.toggle('is-open', open);
  cartDrawer.setAttribute('aria-hidden', open ? 'false' : 'true');
  if(open) $('#closeCart').focus(); else $('#cartButton').focus();
}
async function checkout() {
  const items = Object.entries(cart).filter(([id, quantity]) => catalog.some(p => p.id === id) && quantity > 0)
    .map(([id, quantity]) => ({id, quantity}));
  if (!items.length) return;
  const button = $('#checkoutButton');
  button.disabled = true; button.textContent = 'Processing demo order…';
  $('#cartMessage').textContent = '';
  try {
    const data = await getJSON('/api/v1/checkout', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({items})});
    cart = {}; saveCart();
    $('#cartMessage').textContent = `Demo order ${data.order_id} confirmed! No payment was collected.`;
    toast('Order placed! This was only a demo.');
  } catch(error) {
    $('#cartMessage').textContent = `Could not complete demo checkout: ${error.message}`;
  } finally {button.textContent = 'Place demo order ↗'; updateCart();}
}
async function applyFlags() {
  try {
    const [shipping, darkMode, express] = await Promise.all([
      getJSON('/api/v1/flags/evaluate?flag=free_shipping_banner'),
      getJSON('/api/v1/flags/evaluate?flag=dark_mode_beta'),
      getJSON('/api/v1/flags/evaluate?flag=express_checkout')
    ]);
    $('#shippingBanner').hidden = !shipping.enabled;
    document.body.classList.toggle('demo-dark', darkMode.enabled);
    $('#checkoutButton').textContent = express.enabled ? 'Express demo checkout ↗' : 'Place demo order ↗';
  } catch(error) { console.warn('Demo flag evaluation failed:', error.message); }
}
async function init() {
  $('#cartButton').addEventListener('click', () => toggleCart(true));
  $('#closeCart').addEventListener('click', () => toggleCart(false));
  overlay.addEventListener('click', () => toggleCart(false));
  document.addEventListener('keydown', event => {if(event.key === 'Escape') toggleCart(false);});
  $('#checkoutButton').addEventListener('click', checkout);
  document.querySelectorAll('.filter').forEach(button => button.addEventListener('click', () => {
    activeFilter = button.dataset.filter;
    document.querySelectorAll('.filter').forEach(b => b.classList.toggle('is-active', b === button));
    renderProducts();
  }));
  try {
    catalog = (await getJSON('/api/v1/products')).products;
    renderProducts(); updateCart();
  } catch(error) {productGrid.textContent = `Couldn't load catalog: ${error.message}`;}
  await applyFlags();
}
init();
