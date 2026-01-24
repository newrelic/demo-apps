from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
import logging
import os

from database import Database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Bad Apples Inventory Service")
db = Database()

# Pydantic models
class AppleVariety(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price_per_lb: Decimal
    stock_lbs: int
    orchard_location: Optional[str]
    harvest_season: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class OrderItem(BaseModel):
    id: int
    variety_id: int
    variety_name: str
    quantity_lbs: Decimal
    unit_price: Decimal
    subtotal: Decimal

class Order(BaseModel):
    id: int
    customer_name: str
    customer_email: str
    total_amount: Decimal
    status: str
    created_at: datetime
    items: List[OrderItem]

# Startup and shutdown events
@app.on_event("startup")
async def startup():
    """Initialize database connection pool"""
    await db.connect()
    logger.info("Inventory Service started successfully")

@app.on_event("shutdown")
async def shutdown():
    """Close database connection pool"""
    await db.close()
    logger.info("Inventory Service shut down")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for Docker healthcheck"""
    return {"status": "healthy", "service": "inventory"}

# Get all apple varieties
@app.get("/api/varieties", response_model=List[AppleVariety])
async def get_varieties():
    """Get all apple varieties from catalog"""
    try:
        query = """
            SELECT id, name, description, price_per_lb, stock_lbs,
                   orchard_location, harvest_season, created_at
            FROM apple_varieties
            ORDER BY name
        """
        rows = await db.fetch(query)
        logger.info(f"Fetched {len(rows)} apple varieties")
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Error fetching varieties: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch varieties")

# Get single apple variety
@app.get("/api/varieties/{variety_id}", response_model=AppleVariety)
async def get_variety(variety_id: int):
    """Get a single apple variety by ID"""
    try:
        query = """
            SELECT id, name, description, price_per_lb, stock_lbs,
                   orchard_location, harvest_season, created_at
            FROM apple_varieties
            WHERE id = $1
        """
        row = await db.fetchrow(query, variety_id)

        if not row:
            raise HTTPException(status_code=404, detail="Variety not found")

        logger.info(f"Fetched variety: {row['name']}")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching variety {variety_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch variety")

# Check stock for a variety
@app.get("/api/varieties/{variety_id}/stock")
async def get_stock(variety_id: int):
    """Check stock level for a specific variety"""
    try:
        query = "SELECT stock_lbs FROM apple_varieties WHERE id = $1"
        row = await db.fetchrow(query, variety_id)

        if not row:
            raise HTTPException(status_code=404, detail="Variety not found")

        logger.info(f"Stock check for variety {variety_id}: {row['stock_lbs']} lbs")
        return {"variety_id": variety_id, "stock_lbs": row['stock_lbs']}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking stock for variety {variety_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to check stock")

@app.get("/api/orders/recent", response_model=List[Order])
async def get_recent_orders(limit: int = 50):
    """
    Get recent orders with their items.

    Returns the most recent orders for display on the homepage.
    """
    try:
        # Fetch recent orders
        orders_query = """
            SELECT id, customer_name, customer_email, total_amount,
                   status, created_at
            FROM orders
            ORDER BY created_at DESC
            LIMIT $1
        """
        orders = await db.fetch(orders_query, limit)

        logger.info(f"Fetching {len(orders)} recent orders with items")

        # Build result with order items
        # TODO: Consider optimizing this with a JOIN query for better performance
        result = []
        for order in orders:
            items_query = """
                SELECT oi.id, oi.variety_id, av.name as variety_name,
                       oi.quantity_lbs, oi.unit_price, oi.subtotal
                FROM order_items oi
                JOIN apple_varieties av ON oi.variety_id = av.id
                WHERE oi.order_id = $1
            """
            items = await db.fetch(items_query, order['id'])

            order_dict = dict(order)
            order_dict['items'] = [dict(item) for item in items]
            result.append(order_dict)

        logger.info(f"Returned {len(result)} orders with items")
        return result

    except Exception as e:
        logger.error(f"Error fetching recent orders: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent orders")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 5001))
    uvicorn.run(app, host="0.0.0.0", port=port)
