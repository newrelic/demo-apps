#!/bin/sh
set -e

SEED_MODE=${SEED_MODE:-development}

echo "Starting database seeding in mode: $SEED_MODE"

# Seed apple varieties (same for both modes)
# NOTE: Pink Lady has very low stock (2.5 lbs) to trigger Problem 3 (insufficient stock errors)
# Selenium orders 0.5-5.0 lbs, so ~50% of Pink Lady orders will exceed stock
# This creates ~10-15% error rate across all orders
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    INSERT INTO apple_varieties (name, description, price_per_lb, stock_lbs, orchard_location, harvest_season) VALUES
    ('Honeycrisp', 'Sweet and crispy, perfect for snacking', 3.99, 500, 'North Orchard', 'September-October'),
    ('Granny Smith', 'Tart and firm, great for baking', 2.99, 800, 'East Orchard', 'October-November'),
    ('Fuji', 'Sweet and juicy, popular choice', 3.49, 600, 'West Orchard', 'October-November'),
    ('Gala', 'Mildly sweet with crisp texture', 2.79, 700, 'South Orchard', 'August-September'),
    ('Pink Lady', 'Sweet-tart balance, crunchy', 4.29, 2.5, 'North Orchard', 'November-December');
EOSQL

if [ "$SEED_MODE" = "production" ]; then
    echo "Seeding PRODUCTION data (8 varieties, 1000+ orders)..."

    # Add additional varieties for production
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        INSERT INTO apple_varieties (name, description, price_per_lb, stock_lbs, orchard_location, harvest_season) VALUES
        ('Braeburn', 'Crisp and spicy-sweet', 3.29, 550, 'Central Orchard', 'October'),
        ('Golden Delicious', 'Mellow sweetness, all-purpose', 2.49, 900, 'East Orchard', 'September'),
        ('Ambrosia', 'Low acidity, honey-sweet', 4.49, 300, 'Premium Orchard', 'September-October');
EOSQL

    # Generate 1000 orders using SQL-based approach (sh-compatible)
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-'EOSQL'
        -- Insert 1000 orders with random data
        INSERT INTO orders (customer_name, customer_email, customer_phone, delivery_address, total_amount, status)
        SELECT
            CASE (random() * 9)::int
                WHEN 0 THEN 'John Smith'
                WHEN 1 THEN 'Jane Doe'
                WHEN 2 THEN 'Bob Wilson'
                WHEN 3 THEN 'Alice Johnson'
                WHEN 4 THEN 'Charlie Brown'
                WHEN 5 THEN 'Diana Prince'
                WHEN 6 THEN 'Eve Adams'
                WHEN 7 THEN 'Frank Castle'
                WHEN 8 THEN 'Grace Lee'
                ELSE 'Henry Ford'
            END,
            'customer' || generate_series || '@example.com',
            '555-' || lpad(generate_series::text, 4, '0'),
            generate_series || ' Main St, Anytown USA',
            (random() * 50 + 10)::numeric(10,2),
            CASE WHEN random() < 0.7 THEN 'completed' ELSE 'pending' END
        FROM generate_series(1, 1000);

        -- Insert 2-5 order items for each order
        INSERT INTO order_items (order_id, variety_id, quantity_lbs, unit_price, subtotal)
        SELECT
            o.id,
            (random() * 7 + 1)::int,  -- Random variety 1-8
            (random() * 5 + 0.5)::numeric(10,2),  -- Random quantity 0.5-5.5 lbs
            av.price_per_lb,
            ((random() * 5 + 0.5) * av.price_per_lb)::numeric(10,2)
        FROM orders o
        CROSS JOIN generate_series(1, (random() * 3 + 2)::int)  -- 2-5 items per order
        CROSS JOIN apple_varieties av
        WHERE av.id = (random() * 7 + 1)::int
        LIMIT 3500;  -- Approximately 3.5 items per order on average
EOSQL

    echo "Seeded 1000 orders..."

    echo "Production seeding complete: 8 varieties, 1000 orders"
else
    echo "Seeding DEVELOPMENT data (5 varieties, 3 orders)..."

    # Development mode: just 3 sample orders
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        INSERT INTO orders (customer_name, customer_email, customer_phone, delivery_address, total_amount, status) VALUES
        ('John Doe', 'john@example.com', '555-0100', '123 Main St, Anytown USA', 23.94, 'completed'),
        ('Jane Smith', 'jane@example.com', '555-0101', '456 Oak Ave, Somewhere USA', 31.47, 'pending'),
        ('Bob Wilson', 'bob@example.com', '555-0102', '789 Pine Rd, Elsewhere USA', 19.76, 'completed');

        INSERT INTO order_items (order_id, variety_id, quantity_lbs, unit_price, subtotal) VALUES
        (1, 1, 3.0, 3.99, 11.97),
        (1, 2, 4.0, 2.99, 11.96),
        (2, 3, 5.0, 3.49, 17.45),
        (2, 4, 5.0, 2.79, 13.95),
        (3, 5, 3.5, 4.29, 15.02),
        (3, 1, 1.2, 3.99, 4.79);
EOSQL

    echo "Development seeding complete: 5 varieties, 3 orders"
fi

echo "Database seeding finished successfully"
