from flask import Flask, request, jsonify
from datetime import datetime
import logging
import os
import requests
import json

from database import execute_query, get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get inventory service URL from environment
INVENTORY_SERVICE_URL = os.getenv('INVENTORY_SERVICE_URL', 'http://inventory-service:5001')

@app.route('/health')
def health_check():
    """Health check endpoint for Docker healthcheck"""
    return jsonify({"status": "healthy", "service": "orders"})

def get_current_stock(variety_id):
    """Check current stock for a variety"""
    try:
        response = requests.get(
            f"{INVENTORY_SERVICE_URL}/api/varieties/{variety_id}/stock",
            timeout=5
        )
        if response.status_code == 200:
            return response.json().get('stock_lbs', 0)
        return 0
    except Exception as e:
        logger.error(f"Failed to check stock for variety {variety_id}: {e}")
        return 0

@app.route('/api/orders', methods=['POST'])
def create_order():
    """
    Create a new order.

    Accepts order data with items and processes payment.
    Returns order ID on success.
    """
    try:
        data = request.json

        # Validate required fields
        required_fields = ['customer_name', 'customer_email', 'delivery_address', 'items']
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return jsonify({'error': f'Missing required field: {field}'}), 400

        # Calculate total amount and validate items
        total_amount = 0
        for item in data.get('items', []):
            variety_id = item.get('variety_id')
            quantity_lbs = item.get('quantity_lbs', 0)

            # Check current stock levels
            current_stock = get_current_stock(variety_id)

            # Log stock issues for monitoring
            # TODO: Should we block orders when stock is insufficient?
            # For now, logging for ops team to track oversell situations
            if current_stock < quantity_lbs:
                logger.error(
                    f"Error occurred: Insufficient stock for variety {variety_id}. "
                    f"Requested: {quantity_lbs}lbs, Available: {current_stock}lbs. "
                    f"Order will proceed anyway (overselling inventory)."
                )

            # Calculate price (fetch from inventory service)
            try:
                variety_response = requests.get(
                    f"{INVENTORY_SERVICE_URL}/api/varieties/{variety_id}",
                    timeout=5
                )
                if variety_response.status_code == 200:
                    variety = variety_response.json()
                    unit_price = float(variety['price_per_lb'])
                    total_amount += unit_price * float(quantity_lbs)
            except Exception as e:
                logger.error(f"Error occurred: Failed to fetch price for variety {variety_id}: {e}")
                # Continue anyway with estimated price
                total_amount += 3.0 * float(quantity_lbs)

        # Insert order into database
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Insert order
                cursor.execute("""
                    INSERT INTO orders (customer_name, customer_email, customer_phone,
                                       delivery_address, total_amount, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                    RETURNING id
                """, (
                    data['customer_name'],
                    data['customer_email'],
                    data.get('customer_phone', ''),
                    data['delivery_address'],
                    total_amount
                ))

                order_id = cursor.fetchone()[0]

                # Insert order items
                for item in data['items']:
                    variety_id = item['variety_id']
                    quantity_lbs = item['quantity_lbs']

                    # Get price again
                    try:
                        variety_response = requests.get(
                            f"{INVENTORY_SERVICE_URL}/api/varieties/{variety_id}",
                            timeout=5
                        )
                        if variety_response.status_code == 200:
                            variety = variety_response.json()
                            unit_price = float(variety['price_per_lb'])
                        else:
                            unit_price = 3.0
                    except:
                        unit_price = 3.0

                    subtotal = unit_price * float(quantity_lbs)

                    cursor.execute("""
                        INSERT INTO order_items (order_id, variety_id, quantity_lbs,
                                                 unit_price, subtotal)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (order_id, variety_id, quantity_lbs, unit_price, subtotal))

                conn.commit()

        logger.info(
            f"Order {order_id} created successfully. "
            f"Total amount: ${total_amount:.2f}"
        )

        return jsonify({
            'order_id': order_id,
            'status': 'created',
            'total_amount': total_amount,
            'message': 'Order created successfully'
        }), 201

    except Exception as e:
        logger.error(f"Failed to create order: {e}")
        return jsonify({'error': 'Failed to create order'}), 500

@app.route('/api/orders/<int:order_id>', methods=['GET'])
def get_order(order_id):
    """Get a single order by ID"""
    try:
        query = """
            SELECT id, customer_name, customer_email, customer_phone,
                   delivery_address, total_amount, status, created_at
            FROM orders
            WHERE id = %s
        """
        order = execute_query(query, (order_id,), fetch_one=True)

        if not order:
            return jsonify({'error': 'Order not found'}), 404

        # Get order items
        items_query = """
            SELECT oi.id, oi.variety_id, oi.quantity_lbs, oi.unit_price, oi.subtotal,
                   av.name as variety_name
            FROM order_items oi
            JOIN apple_varieties av ON oi.variety_id = av.id
            WHERE oi.order_id = %s
        """
        items = execute_query(items_query, (order_id,), fetch_all=True)

        order['items'] = items
        logger.info(f"Retrieved order {order_id}")
        return jsonify(order)

    except Exception as e:
        logger.error(f"Error fetching order {order_id}: {e}")
        return jsonify({'error': 'Failed to fetch order'}), 500

@app.route('/api/orders', methods=['GET'])
def get_all_orders():
    """Get all orders"""
    try:
        limit = request.args.get('limit', 100, type=int)
        query = """
            SELECT id, customer_name, customer_email, total_amount, status, created_at
            FROM orders
            ORDER BY created_at DESC
            LIMIT %s
        """
        orders = execute_query(query, (limit,), fetch_all=True)

        logger.info(f"Retrieved {len(orders)} orders")
        return jsonify(orders)

    except Exception as e:
        logger.error(f"Error fetching orders: {e}")
        return jsonify({'error': 'Failed to fetch orders'}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """
    Get service statistics.
    """
    try:
        query = "SELECT COUNT(*) as total_orders FROM orders"
        result = execute_query(query, fetch_one=True)

        return jsonify({
            'total_orders_in_db': result['total_orders'],
            'service': 'orders',
            'status': 'healthy'
        })
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        return jsonify({'error': 'Failed to fetch stats'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5002))
    app.run(host='0.0.0.0', port=port)
