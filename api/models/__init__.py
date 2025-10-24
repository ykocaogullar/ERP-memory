"""
Models package for ERP Memory API.
"""

# Domain models
from .domain import (
    Customer,
    SalesOrder,
    WorkOrder,
    Invoice,
    Payment,
    Task,
    OrderStatus,
    InvoiceStatus,
    WorkOrderStatus,
    TaskStatus,
)

# Memory models
from .memory import (
    Entity,
    EntityRelationship,
    Memory,
    MemoryEntity,
    MemorySummary,
    Session,
    SemanticTriple,
    EntityKind,
    MemoryKind,
    EntityStatus,
    MemoryStatus,
    EntityWithRelationships,
    MemoryWithEntities,
)

# API models
from .api import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    InjectedContext,
    MemoryQueryRequest,
    MemoryQueryResponse,
    EntitySearchRequest,
    EntitySearchResponse,
    EntityDetailRequest,
    EntityDetailResponse,
    ConsolidateRequest,
    ConsolidateResponse,
    SemanticTripleRequest,
    SemanticTripleResponse,
    SemanticQueryRequest,
    SemanticQueryResponse,
    HealthCheckResponse,
    StatsResponse,
)

__version__ = "0.1.0"

__all__ = [
    # Domain
    "Customer",
    "SalesOrder",
    "WorkOrder",
    "Invoice",
    "Payment",
    "Task",
    "OrderStatus",
    "InvoiceStatus",
    "WorkOrderStatus",
    "TaskStatus",
    # Memory
    "Entity",
    "EntityRelationship",
    "Memory",
    "MemoryEntity",
    "MemorySummary",
    "Session",
    "SemanticTriple",
    "EntityKind",
    "MemoryKind",
    "EntityStatus",
    "MemoryStatus",
    "EntityWithRelationships",
    "MemoryWithEntities",
    # API
    "ChatMessage",
    "ChatRequest",
    "ChatResponse",
    "InjectedContext",
    "MemoryQueryRequest",
    "MemoryQueryResponse",
    "EntitySearchRequest",
    "EntitySearchResponse",
    "EntityDetailRequest",
    "EntityDetailResponse",
    "ConsolidateRequest",
    "ConsolidateResponse",
    "SemanticTripleRequest",
    "SemanticTripleResponse",
    "SemanticQueryRequest",
    "SemanticQueryResponse",
    "HealthCheckResponse",
    "StatsResponse",
]
