"""Products endpoint - product catalog."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class Product(BaseModel):
    """Product model."""
    id: int
    name: str
    description: str
    price: float
    in_stock: bool = True


# In-memory product catalog
products_db: List[Product] = [
    Product(id=1, name="Widget", description="A versatile widget", price=50.0, in_stock=True),
    Product(id=2, name="Gadget", description="High-tech gadget", price=125.0, in_stock=True),
    Product(id=3, name="Doohickey", description="Essential doohickey", price=25.0, in_stock=True),
    Product(id=4, name="Thingamajig", description="Premium thingamajig", price=200.0, in_stock=False),
    Product(id=5, name="Whatchamacallit", description="Mystery item", price=99.99, in_stock=True),
]


@router.get("/products", response_model=List[Product])
async def get_products():
    """
    Get all products in the catalog.

    Returns:
        List of all products
    """
    logger.info(f"Fetching {len(products_db)} products")
    return products_db


@router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: int):
    """
    Get a specific product by ID.

    Args:
        product_id: Product ID to fetch

    Returns:
        Product details

    Raises:
        HTTPException: If product not found
    """
    from fastapi import HTTPException

    product = next((p for p in products_db if p.id == product_id), None)
    if not product:
        logger.warning(f"Product {product_id} not found")
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    logger.info(f"Fetched product {product_id}: {product.name}")
    return product
