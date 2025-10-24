"""
Database connection and query utilities

Provides connection pooling and helper methods for database operations
"""

import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from typing import Optional, List, Dict, Any, Tuple
from contextlib import contextmanager
import logging

from api.utils.config import settings

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager with connection pooling"""
    
    def __init__(self):
        """Initialize database connection pool"""
        self.pool: Optional[SimpleConnectionPool] = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Create connection pool"""
        try:
            self.pool = SimpleConnectionPool(
                minconn=1,
                maxconn=10,
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                database=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD
            )
            logger.info("Database connection pool initialized")
            
            # Register pgvector extension for the pool
            conn = self.pool.getconn()
            try:
                register_vector(conn)
            finally:
                self.pool.putconn(conn)
                
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections
        
        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM table")
        """
        conn = None
        try:
            conn = self.pool.getconn()
            register_vector(conn)  # Register vector type for this connection
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                self.pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, dict_cursor: bool = True):
        """
        Context manager for database cursors
        
        Args:
            dict_cursor: If True, returns results as dictionaries
            
        Usage:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM table")
                results = cursor.fetchall()
        """
        with self.get_connection() as conn:
            cursor_factory = RealDictCursor if dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            try:
                yield cursor
            finally:
                cursor.close()
    
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
        fetch_one: bool = False,
        dict_cursor: bool = True
    ) -> Optional[Any]:
        """
        Execute a SELECT query and return results
        
        Args:
            query: SQL query string
            params: Query parameters
            fetch_one: If True, return single row; otherwise return all rows
            dict_cursor: If True, return results as dictionaries
            
        Returns:
            Query results (single row, list of rows, or None)
        """
        with self.get_cursor(dict_cursor=dict_cursor) as cursor:
            cursor.execute(query, params)
            if fetch_one:
                return cursor.fetchone()
            return cursor.fetchall()
    
    def execute_update(
        self,
        query: str,
        params: Optional[Tuple] = None
    ) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query
        
        Args:
            query: SQL query string
            params: Query parameters
            
        Returns:
            Number of rows affected
        """
        with self.get_cursor(dict_cursor=False) as cursor:
            cursor.execute(query, params)
            return cursor.rowcount
    
    def execute_many(
        self,
        query: str,
        params_list: List[Tuple]
    ) -> int:
        """
        Execute a query multiple times with different parameters
        
        Args:
            query: SQL query string
            params_list: List of parameter tuples
            
        Returns:
            Total number of rows affected
        """
        with self.get_cursor(dict_cursor=False) as cursor:
            cursor.executemany(query, params_list)
            return cursor.rowcount
    
    def close(self):
        """Close all database connections in the pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("Database connection pool closed")


# Global database instance
db = Database()


def get_db() -> Database:
    """Get the global database instance"""
    return db
