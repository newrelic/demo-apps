import psycopg2
import psycopg2.extras
import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

def get_db_config():
    """Get database configuration from environment"""
    return {
        'host': os.getenv('DB_HOST', 'postgres'),
        'port': int(os.getenv('DB_PORT', 5432)),
        'database': os.getenv('DB_NAME', 'orchard_db'),
        'user': os.getenv('DB_USER', 'orchard_user'),
        'password': os.getenv('DB_PASSWORD', 'orchard_pass')
    }

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = psycopg2.connect(**get_db_config())
        conn.autocommit = False
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Execute a database query"""
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute(query, params or ())

            if fetch_one:
                result = cursor.fetchone()
                conn.commit()
                return dict(result) if result else None
            elif fetch_all:
                results = cursor.fetchall()
                conn.commit()
                return [dict(row) for row in results]
            else:
                conn.commit()
                return cursor.rowcount
