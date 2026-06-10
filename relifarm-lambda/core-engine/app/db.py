"""Postgres connection pool + thin query helpers."""
import os
from contextlib import contextmanager

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

_pool: pool.SimpleConnectionPool | None = None


def init_pool() -> None:
    """Configure the connection pool without opening any connections yet.

    minconn=0 makes pool creation non-blocking — connections are opened on
    demand via getconn(). This lets FastAPI's startup hook complete in
    milliseconds even if Postgres isn't reachable yet, so App Runner's
    /health probe sees a healthy service and the deployment goes RUNNING
    fast. The retry-until-Postgres-is-up loop lives in main.py's bootstrap
    background task, which doesn't gate the lifespan startup.
    """
    global _pool
    _pool = pool.SimpleConnectionPool(
        minconn=0,
        maxconn=10,
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        dbname=os.environ["POSTGRES_DB"],
    )


def close_pool() -> None:
    if _pool is not None:
        _pool.closeall()


@contextmanager
def cursor():
    if _pool is None:
        raise RuntimeError("DB pool not initialized")
    conn = _pool.getconn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except psycopg2.Error:
        conn.rollback()
        raise
    finally:
        _pool.putconn(conn)
