import asyncpg
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        """Create database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                host=os.getenv('DB_HOST', 'postgres'),
                port=int(os.getenv('DB_PORT', 5432)),
                database=os.getenv('DB_NAME', 'orchard_db'),
                user=os.getenv('DB_USER', 'orchard_user'),
                password=os.getenv('DB_PASSWORD', 'orchard_pass'),
                min_size=2,
                max_size=10
            )
            logger.info("Database connection pool created successfully")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise

    async def close(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")

    async def fetch(self, query, *args):
        """Execute a query and fetch all results"""
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetchrow(self, query, *args):
        """Execute a query and fetch one result"""
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def execute(self, query, *args):
        """Execute a query without fetching results"""
        async with self.pool.acquire() as connection:
            return await connection.execute(query, *args)
