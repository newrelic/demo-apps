"""Orders endpoint - business logic for order management."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class Order(BaseModel):
    """Order model."""
    id: int
    product: str
    amount: float
    status: str = "pending"


class CreateOrderRequest(BaseModel):
    """Request model for creating an order."""
    product: str
    amount: float


# In-memory storage for demo purposes
orders_db: List[Order] = [
    Order(id=1, product="Widget", amount=100.0, status="completed"),
    Order(id=2, product="Gadget", amount=250.0, status="pending"),
    Order(id=3, product="Doohickey", amount=75.5, status="completed"),
]


@router.get("/orders", response_model=List[Order])
async def get_orders():
    """
    Get all orders.

    Returns:
        List of all orders
    """
    logger.info(f"Fetching {len(orders_db)} orders")
    return orders_db


@router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: int):
    """
    Get a specific order by ID.

    Args:
        order_id: Order ID to fetch

    Returns:
        Order details

    Raises:
        HTTPException: If order not found
    """
    from fastapi import HTTPException

    order = next((o for o in orders_db if o.id == order_id), None)
    if not order:
        logger.warning(f"Order {order_id} not found")
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    logger.info(f"Fetched order {order_id}")
    return order


@router.post("/orders", response_model=Order)
async def create_order(request: CreateOrderRequest):
    """
    Create a new order.

    Args:
        request: Order creation request

    Returns:
        Created order
    """
    new_id = max([o.id for o in orders_db], default=0) + 1
    new_order = Order(
        id=new_id,
        product=request.product,
        amount=request.amount,
        status="pending"
    )
    orders_db.append(new_order)

    logger.info(f"Created order {new_id}: {request.product} - ${request.amount}")
    return new_order
