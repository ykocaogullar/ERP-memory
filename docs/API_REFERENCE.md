# ERP Memory System - API Reference

## Overview

This document provides detailed API reference for the ERP Memory System services. The system is built with a modular architecture where each service has a specific responsibility.

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Service Layer                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ Entity          │  │ Semantic        │  │ Domain      │  │
│  │ Extractor       │  │ Relationships   │  │ Queries     │  │
│  │                 │  │                 │  │             │  │
│  │ • Extract       │  │ • Schema        │  │ • Customer  │  │
│  │ • Link          │  │ • Conversational│  │ • Orders    │  │
│  │ • Store         │  │ • Store         │  │ • Invoices  │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Database Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐  │
│  │ Domain Schema   │  │ App Schema      │  │ Extensions  │  │
│  │ (ERP Data)      │  │ (Memory)        │  │             │  │
│  │                 │  │                 │  │ • pgvector  │  │
│  │ • customers     │  │ • entities      │  │ • pg_trgm   │  │
│  │ • orders        │  │ • relationships │  │             │  │
│  │ • invoices      │  │ • memories      │  │             │  │
│  └─────────────────┘  └─────────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Entity Extraction Service

**File**: `api/services/entity_extractor.py`  
**Purpose**: Extract and link entities from conversational text to domain database records

### Key Methods

#### `extract_entities(text, user_id, session_id)`

Extract entities from text using multiple strategies.

**Parameters**:
- `text` (str): Input text to analyze
- `user_id` (str): User identifier
- `session_id` (str): Session identifier

**Returns**: `List[Dict[str, Any]]` - List of entity dictionaries

**Example**:
```python
from api.services.entity_extractor import get_entity_extractor

extractor = get_entity_extractor()
entities = extractor.extract_entities(
    "Check status of SO-1001 for Gai Media", 
    user_id="user123", 
    session_id="session456"
)

# Returns:
# [
#   {
#     'name': 'SO-1001',
#     'type': 'sales_order',
#     'source': 'db',
#     'confidence': 1.0,
#     'external_ref': {'table': 'domain.sales_orders', 'id': '...'}
#   },
#   {
#     'name': 'Gai Media',
#     'type': 'customer',
#     'source': 'db',
#     'confidence': 0.8,
#     'external_ref': {'table': 'domain.customers', 'id': '...'}
#   }
# ]
```

#### `store_entities(entities)`

Store extracted entities in the database.

**Parameters**:
- `entities` (List[Dict[str, Any]]): List of entity dictionaries

**Returns**: `List[int]` - List of entity IDs

#### `find_entity_by_name(name, user_id)`

Find existing entity by name.

**Parameters**:
- `name` (str): Entity name to search for
- `user_id` (str): User identifier

**Returns**: `Optional[Dict[str, Any]]` - Entity dictionary or None

### Entity Types

| Type | Description | Example |
|------|-------------|---------|
| `customer` | Business customers | "Gai Media", "PC Boiler" |
| `sales_order` | Sales order IDs | "SO-1001", "SO-2002" |
| `invoice` | Invoice IDs | "INV-1009", "INV-2201" |
| `work_order` | Work order IDs | "WO-1234" |
| `business_term` | General concepts | "delivery", "payment" |

### Configuration

The service uses these configuration options:

```python
# api/utils/config.py
TRIGRAM_THRESHOLD = 0.3          # Fuzzy matching threshold
ENTITY_EMBEDDING_ENABLED = True   # Generate entity embeddings
```

---

## Semantic Relationship Builder

**File**: `api/services/semantic_relationships.py`  
**Purpose**: Extract and store semantic triples (subject-predicate-object) from database schema and conversations

### Key Methods

#### `build_schema_relationships()`

Extract relationships from foreign key constraints.

**Returns**: `List[Dict[str, Any]]` - List of relationship dictionaries

**Example**:
```python
from api.services.semantic_relationships import get_semantic_relationship_builder

builder = get_semantic_relationship_builder()
relationships = builder.build_schema_relationships()

# Returns:
# [
#   {
#     'subject_entity_id': 1,
#     'predicate': 'issued_to',
#     'object_entity_id': 2,
#     'confidence': 1.0,
#     'source': 'db_schema'
#   }
# ]
```

#### `extract_conversational_relationships(text, entities)`

Extract relationships from conversation text.

**Parameters**:
- `text` (str): Conversation text
- `entities` (List[Dict[str, Any]]): List of entities

**Returns**: `List[Dict[str, Any]]` - List of relationship dictionaries

**Example**:
```python
entities = [{'name': 'Gai Media', 'type': 'customer', 'entity_id': 1}]
relationships = builder.extract_conversational_relationships(
    "Gai Media prefers Friday deliveries", 
    entities
)

# Returns:
# [
#   {
#     'subject_entity_id': 1,
#     'predicate': 'prefers',
#     'object_value': 'Friday deliveries',
#     'confidence': 0.8,
#     'source': 'conversation'
#   }
# ]
```

#### `store_relationships(relationships)`

Store relationships in the database.

**Parameters**:
- `relationships` (List[Dict[str, Any]]): List of relationship dictionaries

**Returns**: `List[int]` - List of relationship IDs

### Relationship Types

| Predicate | Description | Example |
|-----------|-------------|---------|
| `issued_to` | Sales order → Customer | (SO-1001, issued_to, Gai Media) |
| `belongs_to` | Invoice → Sales order | (INV-1009, belongs_to, SO-1001) |
| `pays` | Payment → Invoice | (Payment-123, pays, INV-1009) |
| `prefers` | Customer → Preference | (Gai Media, prefers, Friday deliveries) |
| `requires` | Customer → Requirement | (Gai Media, requires, NET30 terms) |
| `has_policy` | Customer → Policy | (Gai Media, has_policy, Rush orders) |

---

## Domain Query Service

**File**: `api/services/domain_queries.py`  
**Purpose**: Query ERP database and format results for LLM context

### Key Methods

#### `get_customer_data(customer_id)`

Get comprehensive customer data including related entities.

**Parameters**:
- `customer_id` (str): Customer UUID

**Returns**: `Optional[Dict[str, Any]]` - Customer data dictionary

**Example**:
```python
from api.services.domain_queries import get_domain_query_service

service = get_domain_query_service()
data = service.get_customer_data("customer-uuid")

# Returns:
# {
#   'customer': {'name': 'Gai Media', 'industry': 'Entertainment', ...},
#   'orders': [{'so_number': 'SO-1001', 'status': 'in_fulfillment', ...}],
#   'invoices': [{'invoice_number': 'INV-1009', 'amount': 1200.00, ...}],
#   'tasks': [{'title': 'SLA investigation', 'status': 'todo', ...}],
#   'summary': {'total_orders': 5, 'open_invoices': 2, ...}
# }
```

#### `get_sales_order_data(so_id)`

Get sales order with related work orders and invoices.

**Parameters**:
- `so_id` (str): Sales order UUID

**Returns**: `Optional[Dict[str, Any]]` - Sales order data dictionary

#### `get_invoice_data(invoice_id)`

Get invoice with payment history and related order info.

**Parameters**:
- `invoice_id` (str): Invoice UUID

**Returns**: `Optional[Dict[str, Any]]` - Invoice data dictionary

**Example**:
```python
data = service.get_invoice_data("invoice-uuid")

# Returns:
# {
#   'invoice': {'invoice_number': 'INV-1009', 'amount': 1200.00, ...},
#   'payments': [{'amount': 600.00, 'method': 'ACH', ...}],
#   'summary': {'total_amount': 1200.00, 'total_paid': 600.00, 'balance': 600.00, ...}
# }
```

#### `search_customers(query, limit=10)`

Search customers by name using fuzzy matching.

**Parameters**:
- `query` (str): Search query
- `limit` (int): Maximum results

**Returns**: `List[Dict[str, Any]]` - List of customer dictionaries

#### `get_overdue_invoices(days_threshold=0)`

Get invoices that are overdue by specified days.

**Parameters**:
- `days_threshold` (int): Days overdue threshold

**Returns**: `List[Dict[str, Any]]` - List of overdue invoice dictionaries

#### `format_for_llm_context(data, context_type)`

Format domain data for LLM context as semantic triples.

**Parameters**:
- `data` (Dict[str, Any]): Domain data dictionary
- `context_type` (str): Type of context ('customer', 'sales_order', 'invoice')

**Returns**: `str` - Formatted context string

**Example**:
```python
context = service.format_for_llm_context(customer_data, "customer")

# Returns:
# === Customer: Gai Media ===
# • (Customer, industry, Entertainment)
# • (Customer, total_orders, 5)
# • (Customer, open_invoices, 2)
# • (INV-1009, amount, $1200.00)
# • (INV-1009, due_date, 2025-09-30)
# ...
```

---

## Usage Examples

### Complete Entity Extraction Workflow

```python
from api.services.entity_extractor import get_entity_extractor
from api.services.semantic_relationships import get_semantic_relationship_builder
from api.services.domain_queries import get_domain_query_service

# Initialize services
extractor = get_entity_extractor()
builder = get_semantic_relationship_builder()
service = get_domain_query_service()

# Extract entities from user message
user_message = "Check status of SO-1001 for Gai Media and remind them about their Friday delivery preference"
entities = extractor.extract_entities(user_message, "user123", "session456")

# Store entities
entity_ids = extractor.store_entities(entities)

# Extract relationships
relationships = builder.extract_conversational_relationships(user_message, entities)
rel_ids = builder.store_relationships(relationships)

# Get domain data for entities
customer_data = None
for entity in entities:
    if entity['type'] == 'customer' and entity.get('external_ref'):
        customer_id = entity['external_ref']['id']
        customer_data = service.get_customer_data(customer_id)
        break

# Format context for LLM
if customer_data:
    context = service.format_for_llm_context(customer_data, "customer")
    print(context)
```

### Error Handling

```python
try:
    entities = extractor.extract_entities(text, user_id, session_id)
    if not entities:
        print("No entities found in text")
    
    entity_ids = extractor.store_entities(entities)
    print(f"Stored {len(entity_ids)} entities")
    
except Exception as e:
    print(f"Entity extraction failed: {e}")
```

---

## Configuration

### Environment Variables

```bash
# Entity Extraction
TRIGRAM_THRESHOLD=0.3                    # Fuzzy matching threshold
ENTITY_EMBEDDING_ENABLED=true            # Generate entity embeddings

# Semantic Relationships
ENABLE_SEMANTIC_RELATIONSHIPS=true       # Enable relationship extraction
SEMANTIC_SCORE_WEIGHT=0.2               # Weight for semantic scoring

# Database
DB_HOST=localhost
DB_NAME=erp_db
DB_USER=erp_user
DB_PASSWORD=erp_password
```

### Service Configuration

```python
# api/utils/config.py
class Settings(BaseSettings):
    # Entity Extraction
    TRIGRAM_THRESHOLD: float = 0.3
    ENTITY_EMBEDDING_ENABLED: bool = True
    
    # Semantic Relationships
    ENABLE_SEMANTIC_RELATIONSHIPS: bool = True
    SEMANTIC_SCORE_WEIGHT: float = 0.2
```

---

## Testing

### Unit Tests

```bash
# Run Phase 4 tests
python tests/test_phase4_entity_linking.py

# Run all tests
python -m pytest tests/
```

### Integration Tests

```python
# Test with real database
from api.services.entity_extractor import get_entity_extractor

extractor = get_entity_extractor()
entities = extractor.extract_entities(
    "Check status of SO-1001 for Gai Media", 
    "test-user", 
    "test-session"
)
print(f"Found {len(entities)} entities")
```

---

## Performance Considerations

### Entity Extraction
- **Regex patterns**: Very fast (~1ms per text)
- **Fuzzy matching**: Moderate (~50ms per customer)
- **Entity embeddings**: Slow (~200ms per entity)

### Domain Queries
- **Simple queries**: Fast (~10ms)
- **Complex joins**: Moderate (~100ms)
- **Financial calculations**: Fast (~20ms)

### Memory Usage
- **Entity cache**: ~1MB per 1000 entities
- **Embedding cache**: ~6MB per 1000 embeddings (1536 dims × 4 bytes)

---

## Troubleshooting

### Common Issues

1. **No entities found**
   - Check text contains recognizable patterns
   - Verify database has seed data
   - Check trigram threshold setting

2. **Low confidence scores**
   - Adjust `TRIGRAM_THRESHOLD` (lower = more matches)
   - Check entity name variations
   - Verify database connectivity

3. **Missing relationships**
   - Ensure entities are stored first
   - Check relationship patterns in text
   - Verify `ENABLE_SEMANTIC_RELATIONSHIPS=true`

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable debug logging for services
logger = logging.getLogger('api.services.entity_extractor')
logger.setLevel(logging.DEBUG)
```

---

## Next Steps

After mastering these services, continue with:

1. **Phase 5**: Memory System Implementation
   - Memory vectorizer
   - Memory storage
   - Retrieval & synthesis

2. **Phase 6**: API Endpoints
   - FastAPI routes
   - HTTP API implementation

3. **Phase 7**: Testing & Validation
   - End-to-end tests
   - Performance testing
