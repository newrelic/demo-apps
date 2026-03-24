CREATE TABLE apple_varieties (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    price_per_lb NUMERIC(10, 2) NOT NULL,
    stock_lbs NUMERIC(10, 2) NOT NULL DEFAULT 0,
    orchard_location VARCHAR(100),
    harvest_season VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_name VARCHAR(200) NOT NULL,
    customer_email VARCHAR(200) NOT NULL,
    customer_phone VARCHAR(50),
    delivery_address TEXT,
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER REFERENCES orders(id) ON DELETE CASCADE,
    variety_id INTEGER REFERENCES apple_varieties(id),
    quantity_lbs NUMERIC(10, 2) NOT NULL,
    unit_price NUMERIC(10, 2) NOT NULL,
    subtotal NUMERIC(10, 2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
