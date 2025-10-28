"""
System endpoints for health checks and statistics
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from api.utils.database import db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health() -> Dict[str, Any]:
    """
    Health check endpoint
    
    Checks:
    - API service status
    - Database connectivity
    """
    status = "healthy"
    checks = {}
    
    # Check database connection
    try:
        db.execute_query("SELECT 1")
        checks["database"] = "connected"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        status = "degraded"
    
    return {
        "status": status,
        "service": "ERP Memory System API",
        "checks": checks
    }


@router.get("/stats")
async def stats() -> Dict[str, Any]:
    """
    System statistics endpoint
    
    Returns counts of:
    - Customers, orders, invoices
    - Entities and memories
    - Sessions
    """
    try:
        stats_data = {}
        
        # Domain statistics
        stats_data["domain"] = {}
        domain_counts = db.execute_query(
            "SELECT 'customers' as table_name, COUNT(*) as count FROM domain.customers "
            "UNION ALL SELECT 'sales_orders', COUNT(*) FROM domain.sales_orders "
            "UNION ALL SELECT 'invoices', COUNT(*) FROM domain.invoices "
            "UNION ALL SELECT 'payments', COUNT(*) FROM domain.payments"
        )
        
        for row in domain_counts:
            stats_data["domain"][row["table_name"]] = row["count"]
        
        # App statistics
        stats_data["app"] = {}
        app_counts = db.execute_query(
            "SELECT 'entities' as table_name, COUNT(*) as count FROM app.entities "
            "UNION ALL SELECT 'memories', COUNT(*) FROM app.memories "
            "UNION ALL SELECT 'sessions', COUNT(*) FROM app.sessions "
            "UNION ALL SELECT 'relationships', COUNT(*) FROM app.entity_relationships"
        )
        
        for row in app_counts:
            stats_data["app"][row["table_name"]] = row["count"]
        
        return stats_data
        
    except Exception as e:
        logger.error(f"Stats endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

