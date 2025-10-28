"""
Entity management endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict, Any
from api.utils.database import db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/entities")
async def get_entities(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(50, ge=1, le=200, description="Max number of entities to retrieve"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (customer, order, invoice, etc.)"),
    session_id: Optional[str] = Query(None, description="Filter by session ID")
) -> Dict[str, Any]:
    """
    Retrieve entities extracted from conversations
    
    Filters:
    - user_id: Required user identifier
    - limit: Maximum number of entities (1-200)
    - entity_type: Optional entity type filter
    - session_id: Optional session filter
    """
    try:
        # Build query
        query = """
            SELECT 
                entity_id,
                name,
                canonical_name,
                type,
                source,
                external_ref,
                confidence,
                created_at
            FROM app.entities
            WHERE user_id = %s
        """
        params = [user_id]
        
        # Add optional filters
        if entity_type:
            query += " AND type = %s"
            params.append(entity_type)
        
        if session_id:
            query += " AND session_id = %s"
            params.append(session_id)
        
        query += " ORDER BY confidence DESC, created_at DESC LIMIT %s"
        params.append(limit)
        
        entities = db.execute_query(query, tuple(params))
        
        return {
            "entities": entities,
            "count": len(entities)
        }
        
    except Exception as e:
        logger.error(f"Entity retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: int) -> Dict[str, Any]:
    """
    Get detailed information about a specific entity
    """
    try:
        query = """
            SELECT 
                entity_id,
                name,
                canonical_name,
                type,
                source,
                external_ref,
                confidence,
                entity_embedding IS NOT NULL as has_embedding,
                created_at
            FROM app.entities
            WHERE entity_id = %s
        """
        
        entity = db.execute_query(query, (entity_id,), fetch_one=True)
        
        if not entity:
            raise HTTPException(status_code=404, detail="Entity not found")
        
        # Get aliases for this entity
        aliases_query = """
            SELECT alias_text, source, confidence, created_at
            FROM app.entity_aliases
            WHERE canonical_entity_id = %s
            ORDER BY confidence DESC
        """
        aliases = db.execute_query(aliases_query, (entity_id,))
        
        entity["aliases"] = aliases
        
        return entity
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Entity detail error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

