"""Health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    service: str
    version: str = "1.0.0"


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status of the service
    """
    logger.debug("Health check requested")
    return HealthResponse(
        status="healthy",
        service="target-app"
    )
