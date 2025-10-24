"""
Memory Models - Pydantic models for the memory system.

These models represent the memory system entities (entities, relationships,
memories, sessions, etc.) and are used for data validation and serialization
when interacting with the app schema.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Enums
# ============================================================================

class EntityKind(str, Enum):
    """Types of entities that can be stored."""
    CUSTOMER = "customer"
    SALES_ORDER = "sales_order"
    WORK_ORDER = "work_order"
    INVOICE = "invoice"
    PAYMENT = "payment"
    TASK = "task"
    PERSON = "person"
    CONCEPT = "concept"


class MemoryKind(str, Enum):
    """Types of memories that can be stored."""
    FACT = "fact"
    EVENT = "event"
    CONVERSATION = "conversation"
    INSIGHT = "insight"
    PREFERENCE = "preference"


class EntityStatus(str, Enum):
    """Status values for entities."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    MERGED = "merged"


class MemoryStatus(str, Enum):
    """Status values for memories."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUPERSEDED = "superseded"


# ============================================================================
# Memory Models
# ============================================================================

class Entity(BaseModel):
    """Entity from app.entities table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    entity_id: UUID
    kind: EntityKind
    name: str
    canonical_name: str
    domain_id: Optional[UUID] = None
    attributes: dict = Field(default_factory=dict)
    embedding: Optional[List[float]] = None  # Vector field
    status: EntityStatus = EntityStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    
    # For lookups - not in database
    source_ids: Optional[List[UUID]] = Field(default=None, exclude=True)


class EntityRelationship(BaseModel):
    """Entity relationship from app.entity_relationships table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    relationship_id: UUID
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str
    attributes: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class Memory(BaseModel):
    """Memory from app.memories table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    memory_id: UUID
    session_id: Optional[UUID] = None
    content: str
    kind: MemoryKind
    importance: float = Field(ge=0.0, le=1.0, default=0.5)
    embedding: Optional[List[float]] = None  # Vector field
    metadata: dict = Field(default_factory=dict)
    status: MemoryStatus = MemoryStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    accessed_at: datetime
    access_count: int = 0


class MemoryEntity(BaseModel):
    """Memory-Entity association from app.memory_entities table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    memory_id: UUID
    entity_id: UUID
    relevance: float = Field(ge=0.0, le=1.0, default=1.0)
    created_at: datetime


class MemorySummary(BaseModel):
    """Memory summary from app.memory_summaries table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    summary_id: UUID
    session_id: Optional[UUID] = None
    summary_text: str
    summary_of_memory_ids: List[UUID] = Field(default_factory=list)
    time_range_start: datetime
    time_range_end: datetime
    embedding: Optional[List[float]] = None  # Vector field
    created_at: datetime


class Session(BaseModel):
    """Session from app.sessions table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    session_id: UUID
    user_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)


class SemanticTriple(BaseModel):
    """Semantic triple from app.semantic_triples table."""
    
    model_config = ConfigDict(from_attributes=True)
    
    triple_id: UUID
    subject_entity_id: UUID
    predicate: str
    object_value: str
    object_entity_id: Optional[UUID] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source_memory_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Helper Models (not directly mapped to tables)
# ============================================================================

class EntityWithRelationships(BaseModel):
    """Entity with its relationships included."""
    
    entity: Entity
    outgoing_relationships: List[EntityRelationship] = Field(default_factory=list)
    incoming_relationships: List[EntityRelationship] = Field(default_factory=list)


class MemoryWithEntities(BaseModel):
    """Memory with associated entities."""
    
    memory: Memory
    entities: List[Entity] = Field(default_factory=list)
    triples: List[SemanticTriple] = Field(default_factory=list)
