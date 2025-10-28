"""
Consolidation API endpoints

Handles memory consolidation requests and statistics.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from api.services.consolidation import get_consolidation_service
from api.models.api import ConsolidateRequest, ConsolidateResponse, ConsolidationStatsResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize consolidation service
consolidation_service = get_consolidation_service()


@router.post("/consolidate", response_model=ConsolidateResponse)
async def consolidate(request: ConsolidateRequest):
    """
    Trigger memory consolidation for a user.
    
    Consolidates memories from recent sessions into summaries.
    """
    try:
        logger.info(f"Consolidation request for user {request.user_id}, window_size={request.window_size}")
        
        result = consolidation_service.consolidate_sessions(
            user_id=request.user_id,
            window_size=request.window_size
        )
        
        logger.info(f"Consolidation completed: {result['summary_count']} summaries created")
        return ConsolidateResponse(**result)
        
    except Exception as e:
        logger.error(f"Consolidation failed for user {request.user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/consolidate/stats", response_model=ConsolidationStatsResponse)
async def get_consolidation_stats(user_id: str = Query(..., description="User ID to get stats for")):
    """
    Get consolidation statistics for a user.
    
    Returns information about consolidated/unconsolidated sessions and summaries.
    """
    try:
        stats = consolidation_service.get_consolidation_stats(user_id)
        return ConsolidationStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get consolidation stats for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
