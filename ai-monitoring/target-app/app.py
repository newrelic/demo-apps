"""
Target App - Fragile FastAPI service for AI monitoring demo.

This service intentionally includes failure modes that can be triggered
by the Chaos Engine to demonstrate autonomous repair capabilities.
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from state import get_failure_state, clear_failure_state
from failures.crash_handler import handle_crash
from failures.slow_response import handle_slow_response
from failures.config_error import handle_config_error

from endpoints import health, orders, products

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info("Target App starting up...")
    logger.info(f"DATABASE_URL configured: {bool(os.getenv('DATABASE_URL'))}")
    logger.info(f"Failure state file: {os.getenv('FAILURE_STATE_FILE')}")

    # Initialize healthy state on startup
    clear_failure_state()

    yield

    logger.info("Target App shutting down...")


# Create FastAPI application
app = FastAPI(
    title="Target Application",
    description="Intentionally fragile service for AI monitoring demonstration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def failure_injection_middleware(request: Request, call_next):
    """
    Middleware that injects failures based on shared state file.

    This middleware checks the failure state before processing each request
    and triggers the appropriate failure mode:
    - crash: Exit the application
    - slow: Add artificial delay
    - config_error: Raise configuration error
    - healthy: Process normally
    """
    # Skip failure injection for health check endpoint
    if request.url.path == "/health":
        return await call_next(request)

    # Read current failure state
    failure_state = get_failure_state()
    mode = failure_state.get("mode", "healthy")

    logger.debug(f"Processing request {request.url.path} in mode: {mode}")

    # Handle crash mode - exits immediately
    if mode == "crash":
        handle_crash()
        # Note: This line is never reached because handle_crash() calls os._exit()

    # Handle slow response mode - adds delay
    if mode == "slow":
        delay = failure_state.get("delay", 10)
        await handle_slow_response(delay)

    # Handle config error mode - raises exception
    if mode == "config_error":
        handle_config_error()
        # Note: This line is never reached because handle_config_error() raises exception

    # Normal processing for healthy mode
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"}
        )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(orders.router, tags=["Orders"])
app.include_router(products.router, tags=["Products"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "target-app",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "orders": "/orders",
            "products": "/products"
        }
    }


@app.get("/debug/state")
async def get_current_state():
    """
    Debug endpoint to check current failure state.
    Useful for troubleshooting.
    """
    state = get_failure_state()
    return {
        "current_state": state,
        "database_url_configured": bool(os.getenv("DATABASE_URL"))
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
