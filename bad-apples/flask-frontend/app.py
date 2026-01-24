from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'bad-apples-secret-key-change-in-production')

# Custom filter to convert variety names to image filenames
@app.template_filter('variety_image')
def variety_image(variety_name):
    """Convert variety name to image filename"""
    return variety_name.lower().replace(' ', '-') + '.jpg'

# Service URLs
INVENTORY_SERVICE_URL = os.getenv('INVENTORY_SERVICE_URL', 'http://inventory-service:5001')
ORDER_SERVICE_URL = os.getenv('ORDER_SERVICE_URL', 'http://order-service:5002')

@app.route('/health')
def health_check():
    """Health check endpoint for Docker healthcheck"""
    return jsonify({"status": "healthy", "service": "frontend"})

@app.route('/')
def index():
    """Homepage with featured apples and recent orders"""
    try:
        # Fetch apple varieties
        varieties_response = requests.get(
            f"{INVENTORY_SERVICE_URL}/api/varieties",
            timeout=10
        )
        varieties = []
        if varieties_response.status_code == 200:
            varieties = varieties_response.json()
            logger.info(f"Fetched {len(varieties)} apple varieties")
        else:
            logger.error(f"Failed to fetch varieties: {varieties_response.status_code}")

        # Fetch recent orders (triggers N+1 problem in inventory service!)
        recent_orders = []
        try:
            orders_response = requests.get(
                f"{INVENTORY_SERVICE_URL}/api/orders/recent?limit=500",
                timeout=30
            )
            if orders_response.status_code == 200:
                recent_orders = orders_response.json()
                logger.info(f"Fetched {len(recent_orders)} recent orders")
        except Exception as e:
            logger.error(f"Failed to fetch recent orders: {e}")

        return render_template('index.html',
                             varieties=varieties[:5],  # Show top 5 on homepage
                             recent_orders=recent_orders)
    except Exception as e:
        logger.error(f"Error loading homepage: {e}")
        return render_template('index.html', varieties=[], recent_orders=[])

@app.route('/catalog')
def catalog():
    """Full catalog page"""
    try:
        response = requests.get(
            f"{INVENTORY_SERVICE_URL}/api/varieties",
            timeout=10
        )

        if response.status_code == 200:
            varieties = response.json()
            logger.info(f"Displaying catalog with {len(varieties)} varieties")
            return render_template('catalog.html', varieties=varieties)
        else:
            logger.error(f"Failed to fetch varieties: {response.status_code}")
            return render_template('catalog.html', varieties=[])

    except Exception as e:
        logger.error(f"Error loading catalog: {e}")
        return render_template('catalog.html', varieties=[])

@app.route('/variety/<int:variety_id>')
def variety_detail(variety_id):
    """Individual variety detail page"""
    try:
        response = requests.get(
            f"{INVENTORY_SERVICE_URL}/api/varieties/{variety_id}",
            timeout=10
        )

        if response.status_code == 200:
            variety = response.json()
            logger.info(f"Displaying variety: {variety['name']}")
            return render_template('variety_detail.html', variety=variety)
        else:
            logger.error(f"Variety {variety_id} not found")
            return redirect(url_for('catalog'))

    except Exception as e:
        logger.error(f"Error loading variety {variety_id}: {e}")
        return redirect(url_for('catalog'))

@app.route('/cart')
def cart():
    """Shopping cart page"""
    cart_items = session.get('cart', [])
    logger.info(f"Viewing cart with {len(cart_items)} items")
    return render_template('cart.html', cart_items=cart_items)

@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    """Add item to cart (AJAX endpoint)"""
    try:
        data = request.json
        variety_id = data.get('variety_id')
        quantity_lbs = float(data.get('quantity_lbs', 1.0))

        # Fetch variety details
        response = requests.get(
            f"{INVENTORY_SERVICE_URL}/api/varieties/{variety_id}",
            timeout=5
        )

        if response.status_code != 200:
            return jsonify({'error': 'Variety not found'}), 404

        variety = response.json()

        # Get or create cart
        cart = session.get('cart', [])

        # Check if item already in cart
        found = False
        for item in cart:
            if item['variety_id'] == variety_id:
                item['quantity_lbs'] += quantity_lbs
                found = True
                break

        if not found:
            cart.append({
                'variety_id': variety_id,
                'name': variety['name'],
                'price_per_lb': float(variety['price_per_lb']),
                'quantity_lbs': quantity_lbs
            })

        session['cart'] = cart
        logger.info(f"Added {quantity_lbs}lbs of {variety['name']} to cart")

        return jsonify({
            'success': True,
            'cart_size': len(cart),
            'message': f'Added {quantity_lbs}lbs of {variety["name"]} to cart'
        })

    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        return jsonify({'error': 'Failed to add to cart'}), 500

@app.route('/api/cart/remove', methods=['POST'])
def remove_from_cart():
    """Remove item from cart (AJAX endpoint)"""
    try:
        data = request.json
        variety_id = data.get('variety_id')

        cart = session.get('cart', [])
        cart = [item for item in cart if item['variety_id'] != variety_id]
        session['cart'] = cart

        logger.info(f"Removed variety {variety_id} from cart")
        return jsonify({'success': True, 'cart_size': len(cart)})

    except Exception as e:
        logger.error(f"Error removing from cart: {e}")
        return jsonify({'error': 'Failed to remove from cart'}), 500

@app.route('/api/cart/clear', methods=['POST'])
def clear_cart():
    """Clear entire cart"""
    session['cart'] = []
    logger.info("Cart cleared")
    return jsonify({'success': True})

@app.route('/checkout')
def checkout():
    """Checkout page"""
    cart_items = session.get('cart', [])

    if not cart_items:
        logger.info("Checkout attempted with empty cart")
        return redirect(url_for('catalog'))

    total = sum(item['price_per_lb'] * item['quantity_lbs'] for item in cart_items)
    logger.info(f"Checkout page loaded with {len(cart_items)} items, total: ${total:.2f}")

    return render_template('checkout.html', cart_items=cart_items, total=total)

@app.route('/api/checkout', methods=['POST'])
def submit_checkout():
    """
    Submit order (AJAX endpoint).
    This triggers both Problem 2 (memory leak) and Problem 3 (silent errors)
    in the order service.
    """
    try:
        data = request.json
        cart_items = session.get('cart', [])

        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400

        # Prepare order data
        order_data = {
            'customer_name': data.get('customer_name'),
            'customer_email': data.get('customer_email'),
            'customer_phone': data.get('customer_phone', ''),
            'delivery_address': data.get('delivery_address'),
            'items': [
                {
                    'variety_id': item['variety_id'],
                    'quantity_lbs': item['quantity_lbs']
                }
                for item in cart_items
            ]
        }

        # Submit order to order service
        # This will trigger:
        # - Problem 2: Memory leak (order added to unbounded cache)
        # - Problem 3: Silent errors (stock validation logged but not raised)
        response = requests.post(
            f"{ORDER_SERVICE_URL}/api/orders",
            json=order_data,
            timeout=10
        )

        if response.status_code == 201:
            result = response.json()
            order_id = result.get('order_id')

            # Clear cart
            session['cart'] = []

            logger.info(f"Order {order_id} created successfully")
            return jsonify({
                'success': True,
                'order_id': order_id,
                'message': 'Order placed successfully!'
            })
        else:
            logger.error(f"Order creation failed: {response.status_code}")
            return jsonify({'error': 'Failed to create order'}), 500

    except Exception as e:
        logger.error(f"Checkout error: {e}")
        return jsonify({'error': 'Failed to process checkout'}), 500

@app.route('/order/<int:order_id>')
def order_confirmation(order_id):
    """Order confirmation page"""
    try:
        response = requests.get(
            f"{ORDER_SERVICE_URL}/api/orders/{order_id}",
            timeout=10
        )

        if response.status_code == 200:
            order = response.json()
            logger.info(f"Displaying order confirmation for order {order_id}")
            return render_template('order_confirmation.html', order=order)
        else:
            logger.error(f"Order {order_id} not found")
            return redirect(url_for('index'))

    except Exception as e:
        logger.error(f"Error loading order {order_id}: {e}")
        return redirect(url_for('index'))

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
