"""
API Models - Pydantic models for API requests and responses.

These models define the structure of HTTP request and response payloads
for the FastAPI endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from .memory import EntityKind, MemoryKind, Memory, Entity, SemanticTriple


# ============================================================================
# Chat API Models
# ============================================================================

class ChatMessage(BaseModel):
    """A single message in a chat conversation."""
    
    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(default=None, description="When the message was sent")


class ChatRequest(BaseModel):
    """Request payload for chat endpoint."""
    
    messages: List[ChatMessage] = Field(..., description="Conversation history")
    session_id: Optional[UUID] = Field(default=None, description="Session ID for context continuity")
    user_id: Optional[str] = Field(default=None, description="User identifier")
    max_tokens: Optional[int] = Field(default=1000, ge=1, le=4096, description="Max tokens in response")
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    retrieve_memories: bool = Field(default=True, description="Whether to retrieve relevant memories")
    max_memories: int = Field(default=10, ge=1, le=50, description="Max memories to retrieve")
    create_memories: bool = Field(default=True, description="Whether to create new memories from conversation")


class InjectedContext(BaseModel):
    """Context that was injected into the LLM prompt."""
    
    memories: List[Memory] = Field(default_factory=list, description="Retrieved memories")
    entities: List[Entity] = Field(default_factory=list, description="Relevant entities")
    domain_facts: List[Dict[str, Any]] = Field(default_factory=list, description="Facts from ERP database")
    semantic_triples: List[SemanticTriple] = Field(default_factory=list, description="Relevant semantic triples")


class ChatResponse(BaseModel):
    """Response payload for chat endpoint."""
    
    response: str = Field(..., description="Assistant's response")
    session_id: UUID = Field(..., description="Session ID (created if not provided)")
    injected_context: Optional[InjectedContext] = Field(default=None, description="Context used to generate response")
    memories_created: int = Field(default=0, description="Number of new memories created")
    entities_linked: int = Field(default=0, description="Number of entities linked")
    usage: Optional[Dict[str, int]] = Field(default=None, description="Token usage stats")


# ============================================================================
# Memory Query API Models
# ============================================================================

class MemoryQueryRequest(BaseModel):
    """Request payload for querying memories."""
    
    query: str = Field(..., description="Query text for semantic search")
    session_id: Optional[UUID] = Field(default=None, description="Filter by session")
    memory_kinds: Optional[List[MemoryKind]] = Field(default=None, description="Filter by memory types")
    entity_ids: Optional[List[UUID]] = Field(default=None, description="Filter by associated entities")
    min_importance: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum importance score")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    include_archived: bool = Field(default=False, description="Include archived memories")


class MemoryQueryResponse(BaseModel):
    """Response payload for memory query."""
    
    memories: List[Memory] = Field(..., description="Retrieved memories")
    count: int = Field(..., description="Number of results returned")


# ============================================================================
# Entity API Models
# ============================================================================

class EntitySearchRequest(BaseModel):
    """Request payload for entity search."""
    
    query: str = Field(..., description="Search query")
    entity_kinds: Optional[List[EntityKind]] = Field(default=None, description="Filter by entity types")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    use_fuzzy: bool = Field(default=True, description="Enable fuzzy text matching")


class EntitySearchResponse(BaseModel):
    """Response payload for entity search."""
    
    entities: List[Entity] = Field(..., description="Found entities")
    count: int = Field(..., description="Number of results")


class EntityDetailRequest(BaseModel):
    """Request payload for entity detail retrieval."""
    
    entity_id: UUID = Field(..., description="Entity ID")
    include_relationships: bool = Field(default=True, description="Include relationships")
    include_memories: bool = Field(default=True, description="Include related memories")
    include_triples: bool = Field(default=True, description="Include semantic triples")


class EntityDetailResponse(BaseModel):
    """Response payload for entity detail."""
    
    entity: Entity = Field(..., description="Entity details")
    relationships: Optional[List[Dict[str, Any]]] = Field(default=None, description="Entity relationships")
    memories: Optional[List[Memory]] = Field(default=None, description="Related memories")
    triples: Optional[List[SemanticTriple]] = Field(default=None, description="Semantic triples")


# ============================================================================
# Consolidation API Models
# ============================================================================

class ConsolidateRequest(BaseModel):
    """Request payload for memory consolidation."""
    
    session_id: Optional[UUID] = Field(default=None, description="Consolidate specific session (or all if None)")
    min_memories: int = Field(default=5, ge=2, description="Minimum memories required for consolidation")
    importance_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Min importance to consider")


class ConsolidateResponse(BaseModel):
    """Response payload for consolidation."""
    
    summaries_created: int = Field(..., description="Number of summaries created")
    memories_consolidated: int = Field(..., description="Number of memories consolidated")
    session_ids: List[UUID] = Field(..., description="Sessions that were consolidated")


# ============================================================================
# Semantic Layer API Models
# ============================================================================

class SemanticTripleRequest(BaseModel):
    """Request payload for creating semantic triples."""
    
    subject_entity_id: UUID = Field(..., description="Subject entity")
    predicate: str = Field(..., description="Relationship predicate")
    object_value: str = Field(..., description="Object value or description")
    object_entity_id: Optional[UUID] = Field(default=None, description="Object entity ID if applicable")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    source_memory_id: Optional[UUID] = Field(default=None, description="Source memory")


class SemanticTripleResponse(BaseModel):
    """Response payload for triple creation."""
    
    triple: SemanticTriple = Field(..., description="Created triple")


class SemanticQueryRequest(BaseModel):
    """Request payload for semantic queries."""
    
    subject: Optional[str] = Field(default=None, description="Subject entity name or ID")
    predicate: Optional[str] = Field(default=None, description="Relationship predicate")
    object_value: Optional[str] = Field(default=None, description="Object value pattern")
    max_results: int = Field(default=20, ge=1, le=100, description="Maximum results")


class SemanticQueryResponse(BaseModel):
    """Response payload for semantic query."""
    
    triples: List[SemanticTriple] = Field(..., description="Matching triples")
    count: int = Field(..., description="Number of results")


# ============================================================================
# System API Models
# ============================================================================

class HealthCheckResponse(BaseModel):
    """Response for health check endpoint."""
    
    status: str = Field(..., description="System status: 'healthy' or 'unhealthy'")
    database: str = Field(..., description="Database connection status")
    vector_store: str = Field(..., description="Vector store status")
    timestamp: datetime = Field(..., description="Check timestamp")


class StatsResponse(BaseModel):
    """Response for system statistics."""
    
    total_memories: int = Field(..., description="Total memories in system")
    total_entities: int = Field(..., description="Total entities")
    total_sessions: int = Field(..., description="Total sessions")
    total_triples: int = Field(..., description="Total semantic triples")
    active_memories: int = Field(..., description="Active memories")
    active_entities: int = Field(..., description="Active entities")
