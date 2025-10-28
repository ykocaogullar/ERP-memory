"""
Memory management endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from api.services.memory_storage import get_memory_storage
from api.utils.database import db
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
memory_storage = get_memory_storage()


@router.get("/memory")
async def get_memories(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(10, ge=1, le=100, description="Max number of memories to retrieve"),
    kind: Optional[str] = Query(None, description="Filter by memory kind (episodic, semantic, profile, policy, commitment, todo)"),
    session_id: Optional[str] = Query(None, description="Filter by session ID")
) -> Dict[str, Any]:
    """
    Retrieve stored memories for a user
    
    Filters:
    - user_id: Required user identifier
    - limit: Maximum number of memories (1-100)
    - kind: Optional memory type filter
    - session_id: Optional session filter
    """
    try:
        # Query memories from database
        query = """
            SELECT 
                memory_id,
                text,
                kind,
                importance,
                created_at,
                expires_at
            FROM app.memories
            WHERE user_id = %s
            AND (expires_at IS NULL OR expires_at > NOW())
        """
        params = [user_id]
        
        # Add optional filters
        if kind:
            query += " AND kind = %s"
            params.append(kind)
        
        if session_id:
            query += " AND session_id = %s"
            params.append(session_id)
        
        query += " ORDER BY importance DESC, created_at DESC LIMIT %s"
        params.append(limit)
        
        memories = db.execute_query(query, tuple(params))
        
        return {
            "memories": memories,
            "count": len(memories)
        }
        
    except Exception as e:
        logger.error(f"Memory retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/{memory_id}")
async def delete_memory(memory_id: int) -> Dict[str, Any]:
    """
    Delete a specific memory by ID
    """
    try:
        query = "DELETE FROM app.memories WHERE memory_id = %s RETURNING memory_id"
        result = db.execute_query(query, (memory_id,))
        
        if not result:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        return {"message": "Memory deleted", "memory_id": memory_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory deletion error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

