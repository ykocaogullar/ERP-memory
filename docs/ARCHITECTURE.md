# ERP Memory System - Architecture

## Overview

This document describes the core architecture and components of the ERP Memory System.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI Application                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Routes     │  │   Services   │  │   Models     │      │
│  │              │  │              │  │              │      │
│  │ /chat        │→ │ Entity Link  │→ │ Domain       │      │
│  │ /memories    │→ │ Embeddings   │→ │ Memory       │      │
│  │ /entities    │→ │ Semantic     │→ │ API          │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                           ↓                                  │
│                    ┌──────────────┐                         │
│                    │  Database    │                         │
│                    │  Connection  │                         │
│                    │  Pool        │                         │
│                    └──────────────┘                         │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
                    ┌──────────────────┐
                    │   PostgreSQL     │
                    │   + pgvector     │
                    │                  │
                    │  - domain schema │
                    │  - app schema    │
                    └──────────────────┘
```

## Project Structure

```
ERP-memory/
├── api/                      # Core API application
│   ├── models/              # Pydantic data models
│   │   ├── domain.py        # ERP domain entities (Customer, Order, etc.)
│   │   ├── memory.py        # Memory system entities (Entity, Memory, etc.)
│   │   └── api.py           # API request/response models
│   ├── services/            # Business logic services
│   │   ├── embeddings.py    # OpenAI embedding service
│   │   ├── entity_extractor.py      # Entity extraction & linking
│   │   ├── semantic_relationships.py # Semantic triple extraction
│   │   └── domain_queries.py        # ERP data queries
│   ├── routes/              # FastAPI route handlers (Phase 6)
│   └── utils/               # Utility modules
│       ├── config.py        # Configuration management
│       └── database.py      # Database connection pooling
├── db/                      # Database files
│   ├── migrations/          # SQL migration scripts
│   └── seeds/               # Sample data
├── docs/                    # Documentation
│   ├── SETUP.md            # Setup & installation guide
│   └── ARCHITECTURE.md     # This file - architecture & components
├── tests/                   # Test files
└── .env                     # Environment configuration (not in git)
```

## Core Components

### Configuration (`api/utils/config.py`)

**Purpose**: Centralized, type-safe configuration management

**Features**:
- Loads settings from `.env` file using `pydantic-settings`
- Type validation (e.g., port must be integer, not string)
- Required field validation (fails fast if OpenAI key missing)
- Default values for optional settings
- IDE autocomplete support

**Usage**:
```python
from api.utils.config import settings

print(settings.DB_NAME)           # "erp_db"
print(settings.EMBEDDING_MODEL)   # "text-embedding-3-small"
print(settings.OPENAI_API_KEY)    # Validated at startup
```

**Key Settings**:
- Database: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- OpenAI: `OPENAI_API_KEY`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSION`, `LLM_MODEL`
- Memory: `ENABLE_VECTORS`, `MEMORY_TTL_DAYS`, `CONSOLIDATION_WINDOW`

---

### Database (`api/utils/database.py`)

**Purpose**: Efficient database connection management and query execution

**Features**:
- Connection pooling (5 min, 20 max connections) - reuses connections instead of creating new ones
- Returns dictionaries instead of tuples for easier data access
- Context managers for automatic resource cleanup
- Automatic pgvector extension registration
- Helper methods for common query patterns

**Usage**:
```python
from api.utils.database import db

# Simple query - returns list of dicts
customers = db.execute_query(
    "SELECT * FROM domain.customers WHERE industry = %s",
    params=("Entertainment",)
)

# Single result
customer = db.execute_query(
    "SELECT * FROM domain.customers WHERE customer_id = %s",
    params=(customer_id,),
    fetch_one=True
)

# Insert/Update/Delete
rows_affected = db.execute_update(
    "UPDATE domain.customers SET notes = %s WHERE customer_id = %s",
    params=("VIP customer", customer_id)
)

# Manual connection management (advanced)
with db.get_connection() as conn:
    with db.get_cursor(conn) as cur:
        cur.execute("SELECT ...")
        result = cur.fetchall()
```

**Why Connection Pooling?**
- Without: Each request creates new connection (~50ms overhead)
- With: Reuses existing connections (~1ms overhead)
- Critical for meeting <800ms latency target

---

### Models (`api/models/`)

**Purpose**: Data validation and type safety using Pydantic

#### Domain Models (`domain.py`)
Represent ERP business entities - map to `domain.*` database tables.

**Models** (6 total):
- `Customer`: customer_id, name, industry, notes, created_at
- `SalesOrder`: so_id, customer_id, so_number, title, status, created_at
- `WorkOrder`: wo_id, so_id, description, status, technician, scheduled_for
- `Invoice`: invoice_id, so_id, invoice_number, amount, due_date, status, issued_at
- `Payment`: payment_id, invoice_id, amount, method, paid_at
- `Task`: task_id, customer_id, title, body, status, created_at

**Enums**:
- `OrderStatus`: draft, approved, in_fulfillment, fulfilled, cancelled
- `InvoiceStatus`: open, paid, void
- `WorkOrderStatus`: queued, in_progress, blocked, done
- `TaskStatus`: todo, doing, done

**Usage**:
```python
from api.models import Customer, OrderStatus

# Fetch from database
row = db.execute_query("SELECT * FROM domain.customers LIMIT 1", fetch_one=True)

# Validate and convert to model
customer = Customer(**row)

# Type-safe access with autocomplete
print(customer.name)        # str
print(customer.customer_id) # UUID
print(customer.created_at)  # datetime
```

#### Memory Models (`memory.py`)
Represent the memory system - map to `app.*` database tables.

**Core Models** (7 main + 2 helpers):
- `Entity`: Extracted entities with embeddings (customers, concepts, people)
- `EntityRelationship`: Connections between entities
- `Memory`: Individual memories with vector embeddings
- `MemoryEntity`: Links memories to entities
- `MemorySummary`: Consolidated summaries of multiple memories
- `Session`: User conversation sessions
- `SemanticTriple`: Knowledge graph triples (subject-predicate-object)

**Helpers**:
- `EntityWithRelationships`: Entity + its relationships
- `MemoryWithEntities`: Memory + associated entities

**Key Fields**:
```python
class Entity:
    entity_id: UUID
    kind: EntityKind              # customer, order, concept, person
    name: str                     # "Gai Media"
    canonical_name: str           # "gai_media" (normalized)
    domain_id: Optional[UUID]     # Link to domain table
    embedding: List[float]        # 1536-dimension vector
    attributes: dict              # Flexible JSON data

class Memory:
    memory_id: UUID
    content: str                  # "Customer asked about order status"
    kind: MemoryKind             # fact, event, conversation, insight
    importance: float            # 0.0 to 1.0
    embedding: List[float]       # 1536-dimension vector
    metadata: dict               # Flexible JSON data
    access_count: int            # Usage tracking
    accessed_at: datetime        # Last access time
```

#### API Models (`api.py`)
Request and response models for FastAPI endpoints.

**Categories** (14 models total):
- **Chat**: `ChatRequest`, `ChatResponse`, `ChatMessage`, `InjectedContext`
- **Memory Query**: `MemoryQueryRequest`, `MemoryQueryResponse`
- **Entity Search**: `EntitySearchRequest`, `EntitySearchResponse`, `EntityDetailRequest`, `EntityDetailResponse`
- **Consolidation**: `ConsolidateRequest`, `ConsolidateResponse`
- **Semantic**: `SemanticTripleRequest`, `SemanticQueryRequest`, `SemanticQueryResponse`
- **System**: `HealthCheckResponse`, `StatsResponse`

**Example**:
```python
class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    session_id: Optional[UUID]
    retrieve_memories: bool = True
    max_memories: int = 10
    temperature: float = 0.7

class ChatResponse(BaseModel):
    response: str                      # LLM's answer
    session_id: UUID                   # Session ID
    injected_context: InjectedContext  # What context was used
    memories_created: int              # How many new memories
    entities_linked: int               # How many entities referenced
```

---

### Embedding Service (`api/services/embeddings.py`)

**Purpose**: Generate text embeddings using OpenAI for semantic search

**Features**:
- Single text embedding generation
- Batch embedding (efficient for multiple texts)
- In-memory LRU caching (1000 most recent embeddings)
- Cosine similarity calculation
- Error handling and validation

**Model**: `text-embedding-3-small` (1536 dimensions)

**Usage**:
```python
from api.services import get_embedding_service

service = get_embedding_service()

# Single embedding
vector = service.embed_text("What is the status of order SO-1001?")
# Returns: [0.123, -0.456, 0.789, ...] (1536 floats)

# Batch embedding (more efficient)
texts = [
    "Customer Gai Media",
    "Sales Order SO-1001",
    "Invoice INV-1009"
]
vectors = service.embed_batch(texts)
# Returns: [[...], [...], [...]] (3 x 1536)

# With caching (for frequently used text like entity names)
vector = service.embed_text("Gai Media", use_cache=True)

# Similarity
similarity = service.cosine_similarity(vec1, vec2)
# Returns: 0.0 to 1.0 (higher = more similar)
```

**How Embeddings Work**:
1. Text → OpenAI API → 1536-dimensional vector
2. Similar meaning = vectors are close in vector space
3. Store vectors in database (pgvector)
4. Search: Query → vector → find nearest neighbors

**Caching Strategy**:
- LRU cache stores last 1000 embeddings in RAM
- Good for: Entity names, common queries (avoid repeated API calls)
- Not good for: Unique user messages (every message is different)
- Cache cleared on restart (not persistent)

---

### Entity Extraction Service (`api/services/entity_extractor.py`)

**Purpose**: Extract and link entities from conversational text to domain database records

**Features**:
- **Deterministic extraction**: Regex patterns for SO/INV/WO IDs
- **Fuzzy matching**: Trigram similarity for customer names
- **Semantic extraction**: Business term recognition
- **Confidence scoring**: Multi-factor scoring with recency boost
- **Entity embeddings**: Optional 1536-dimensional vectors for semantic similarity
- **PII-safe hashing**: Secure entity name hashing

**Usage**:
```python
from api.services.entity_extractor import get_entity_extractor

extractor = get_entity_extractor()

# Extract entities from text
entities = extractor.extract_entities(
    "Check status of SO-1001 for Gai Media", 
    user_id="user123", 
    session_id="session456"
)

# Store entities in database
entity_ids = extractor.store_entities(entities)

# Find existing entity
entity = extractor.find_entity_by_name("Gai Media", "user123")
```

**Entity Types**:
- `customer`: Business customers (Gai Media, PC Boiler)
- `sales_order`: Sales order IDs (SO-1001, SO-2002)
- `invoice`: Invoice IDs (INV-1009, INV-2201)
- `work_order`: Work order IDs (WO-1234)
- `business_term`: General business concepts (delivery, payment)

---

### Semantic Relationship Builder (`api/services/semantic_relationships.py`)

**Purpose**: Extract and store semantic triples (subject-predicate-object) from database schema and conversations

**Features**:
- **Schema relationships**: Extract from foreign key constraints
- **Conversational relationships**: Pattern-based extraction from user text
- **Relationship storage**: Store as semantic triples with embeddings
- **Relationship search**: Semantic similarity search for relationships

**Usage**:
```python
from api.services.semantic_relationships import get_semantic_relationship_builder

builder = get_semantic_relationship_builder()

# Build relationships from database schema
schema_rels = builder.build_schema_relationships()

# Extract from conversation
conv_rels = builder.extract_conversational_relationships(
    "Gai Media prefers Friday deliveries", 
    entities
)

# Store relationships
rel_ids = builder.store_relationships(schema_rels + conv_rels)
```

**Relationship Types**:
- `issued_to`: Sales order → Customer
- `belongs_to`: Invoice → Sales order
- `pays`: Payment → Invoice
- `prefers`: Customer → Preference
- `requires`: Customer → Requirement
- `has_policy`: Customer → Policy

---

### Domain Query Service (`api/services/domain_queries.py`)

**Purpose**: Query ERP database and format results for LLM context

**Features**:
- **Comprehensive data access**: Customer, order, invoice, payment data
- **Financial summaries**: Calculate balances, overdue amounts
- **LLM context formatting**: Structure data as semantic triples
- **Search capabilities**: Fuzzy customer search, status-based queries

**Usage**:
```python
from api.services.domain_queries import get_domain_query_service

service = get_domain_query_service()

# Get comprehensive customer data
customer_data = service.get_customer_data("customer-uuid")

# Get invoice with payment history
invoice_data = service.get_invoice_data("invoice-uuid")

# Search customers
customers = service.search_customers("Gai Media")

# Format for LLM context
context = service.format_for_llm_context(customer_data, "customer")
```

**Query Methods**:
- `get_customer_data()`: Complete customer profile with orders, invoices, tasks
- `get_sales_order_data()`: Order details with work orders and invoices
- `get_invoice_data()`: Invoice with payment history and balance
- `get_overdue_invoices()`: Find overdue invoices by days threshold
- `get_work_orders_by_status()`: Filter work orders by status
- `get_customer_financial_summary()`: Financial overview for customer

---

## Database Schema

### Domain Schema (`domain.*`)

Business entities from the ERP system.

**Tables** (6):
- `customers` (3 records) - Customer information
- `sales_orders` (2 records) - Sales orders
- `work_orders` (2 records) - Work orders for fulfillment
- `invoices` (2 records) - Invoices
- `payments` (1 record) - Payments
- `tasks` (2 records) - Support tasks

### App Schema (`app.*`)

Memory system storage.

**Tables** (7):
- `chat_events` - Raw conversation messages
- `entities` - Extracted entities with embeddings (1536-d vector)
- `entity_aliases` - Alternative names for entities
- `entity_relationships` - Semantic relationships between entities
- `memories` - Vector memories with embeddings (1536-d vector)
- `memory_summaries` - Consolidated summaries with embeddings
- `sessions` - User session metadata

**Vector Indexes** (4):
- `idx_entities_embedding` - IVFFlat index for entity similarity
- `idx_memories_embedding` - IVFFlat index for memory similarity
- `idx_summaries_embedding` - IVFFlat index for summary similarity
- `idx_relationships_embedding` - IVFFlat index for relationship similarity

---

## Development Workflow

### Running Tests

```bash
# Activate virtual environment
source .venv/bin/activate

# Test database connection
python tests/test_db_connection.py

# Test all core components
python tests/test_core_components.py
```

### Adding a New Model

1. Define in appropriate file (`domain.py`, `memory.py`, or `api.py`)
2. Add to `__init__.py` exports
3. Add validation tests
4. Update this documentation

### Adding a New Service

1. Create in `api/services/your_service.py`
2. Export in `api/services/__init__.py`
3. Add tests in `tests/`
4. Document usage patterns

---

## Design Decisions

### Why Pydantic for Models?
- Type safety (catch errors at development time)
- Automatic validation (invalid data rejected)
- JSON serialization built-in (perfect for FastAPI)
- IDE autocomplete support

### Why Connection Pooling?
- Performance: Reusing connections is 50x faster than creating new ones
- Scalability: Limited number of DB connections (max 20)
- Required to meet <800ms latency target

### Why In-Memory LRU Cache?
- Simple: No external dependencies (Redis, Memcached)
- Fast: Direct RAM access
- Good enough: For 6-8 hour take-home project
- Could upgrade to Redis for production

### Why Separate Domain/Memory/API Models?
- **Domain**: Reflects database schema exactly
- **Memory**: Memory system entities (different lifecycle)
- **API**: User-facing contracts (can evolve independently)
- Separation of concerns makes testing easier

---

## Performance Considerations

**Target**: <800ms p95 latency for /chat endpoint

**Breakdown**:
- Entity extraction: ~50ms
- Vector search: ~100ms
- LLM call: ~500ms
- Memory storage: ~50ms
- **Total**: ~700ms (100ms buffer)

**Optimizations**:
- ✅ Connection pooling (saves ~50ms per query)
- ✅ Batch embeddings (saves ~200ms for multiple texts)
- ✅ LRU caching (saves ~100ms for repeated embeddings)
- 🔄 IVFFlat indexes (fast approximate nearest neighbor search)
- 🔄 Limit top-k results (10-20 memories max)

---

## Next Steps

See `docs/SETUP.md` for installation and deployment instructions.

For implementation details, see:
- `documents/IMPLEMENTATION_PLAN.md` - Detailed implementation plan
- `private_docs/for-LLM/TECHNICAL_REFERENCE.md` - Code patterns and examples
