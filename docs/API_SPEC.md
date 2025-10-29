# API Specification

Simple API reference for ERP Memory System endpoints.

Base URL: `http://localhost:8080`

---

## System Endpoints

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "ERP Memory System API",
  "checks": {
    "database": "connected"
  }
}
```

**Example:**
```bash
curl http://localhost:8080/health
```

---

### GET /stats

Get system statistics (counts of customers, orders, entities, memories, etc.).

**Response:**
```json
{
  "domain": {
    "customers": 3,
    "sales_orders": 2,
    "invoices": 2,
    "payments": 1
  },
  "app": {
    "entities": 22,
    "memories": 8,
    "sessions": 6,
    "relationships": 0
  }
}
```

**Example:**
```bash
curl http://localhost:8080/stats
```

---

## Chat Endpoint

### POST /api/v1/chat

Process chat message with full memory pipeline.

**Request Body:**
```json
{
  "messages": [
    {
      "role": "user",
      "content": "What is the status of SO-1001?",
      "timestamp": null
    }
  ],
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user-123",
  "max_tokens": 1000,
  "temperature": 0.7,
  "retrieve_memories": true,
  "max_memories": 5,
  "create_memories": true
}
```

**Fields:**
- `messages` (array, required): List of chat messages. Must include at least one user message.
  - `role` (string): "user" or "assistant"
  - `content` (string): Message text
  - `timestamp` (string, optional): ISO timestamp
- `session_id` (string, optional): Session UUID. Auto-generated if not provided.
- `user_id` (string, optional): User identifier. Defaults to "anonymous".
- `max_tokens` (integer, optional): Max tokens for LLM response. Default: 2000.
- `temperature` (float, optional): LLM temperature. Default: 0.7.
- `retrieve_memories` (boolean, optional): Whether to retrieve memories. Default: true.
- `max_memories` (integer, optional): Maximum memories to retrieve. Default: 10.
- `create_memories` (boolean, optional): Whether to create new memories. Default: true.

**Response:**
```json
{
  "response": "SO-1001 is currently in 'pending' status...",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "injected_context": {
    "memories": [],
    "entities": [],
    "domain_facts": [],
    "semantic_triples": []
  },
  "memories_created": 3,
  "entities_linked": 2,
  "usage": {
    "prompt_tokens": 150,
    "completion_tokens": 50
  }
}
```

**Example:**
```bash
curl -X POST "http://localhost:8080/api/v1/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "role": "user",
      "content": "What is the status of SO-1001?",
      "timestamp": null
    }],
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "user-123",
    "max_tokens": 1000,
    "temperature": 0.7,
    "retrieve_memories": true,
    "max_memories": 5,
    "create_memories": true
  }'
```

---

## Memory Endpoints

### GET /api/v1/memory

Retrieve stored memories for a user.

**Query Parameters:**
- `user_id` (string, required): User identifier
- `limit` (integer, optional): Max memories to return (1-100). Default: 10.
- `kind` (string, optional): Filter by memory kind: `episodic`, `semantic`, `profile`, `policy`, `commitment`, `todo`
- `session_id` (string, optional): Filter by session ID

**Response:**
```json
{
  "memories": [
    {
      "memory_id": 1,
      "text": "User asked about SO-1001 order status",
      "kind": "episodic",
      "importance": 0.8,
      "created_at": "2025-01-15T10:30:00Z",
      "expires_at": null
    }
  ],
  "count": 1
}
```

**Example:**
```bash
curl "http://localhost:8080/api/v1/memory?user_id=user-123&limit=10&kind=episodic"
```

---

### DELETE /api/v1/memory/{memory_id}

Delete a specific memory by ID.

**Path Parameters:**
- `memory_id` (integer, required): Memory ID to delete

**Response:**
```json
{
  "message": "Memory deleted",
  "memory_id": 1
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:8080/api/v1/memory/1"
```

---

## Entity Endpoints

### GET /api/v1/entities

Retrieve entities extracted from conversations.

**Query Parameters:**
- `user_id` (string, required): User identifier
- `limit` (integer, optional): Max entities to return (1-200). Default: 50.
- `entity_type` (string, optional): Filter by entity type (customer, order, invoice, etc.)
- `session_id` (string, optional): Filter by session ID

**Response:**
```json
{
  "entities": [
    {
      "entity_id": 1,
      "name": "Gai Media",
      "canonical_name": "Gai Media",
      "type": "customer",
      "source": "conversation",
      "external_ref": {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "type": "customer"
      },
      "confidence": 0.95,
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "count": 1
}
```

**Example:**
```bash
curl "http://localhost:8080/api/v1/entities?user_id=user-123&limit=20&entity_type=customer"
```

---

### GET /api/v1/entities/{entity_id}

Get detailed information about a specific entity.

**Path Parameters:**
- `entity_id` (integer, required): Entity ID

**Response:**
```json
{
  "entity_id": 1,
  "name": "Gai Media",
  "canonical_name": "Gai Media",
  "type": "customer",
  "source": "conversation",
  "external_ref": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "type": "customer"
  },
  "confidence": 0.95,
  "has_embedding": true,
  "created_at": "2025-01-15T10:30:00Z",
  "aliases": [
    {
      "alias_text": "Gai",
      "source": "conversation",
      "confidence": 0.8,
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

**Example:**
```bash
curl "http://localhost:8080/api/v1/entities/1"
```

---

## Consolidation Endpoints

### POST /api/v1/consolidate

Trigger memory consolidation for a user's recent sessions.

**Request Body:**
```json
{
  "user_id": "user-123",
  "window_size": 3
}
```

**Fields:**
- `user_id` (string, required): User identifier
- `window_size` (integer, optional): Number of recent unconsolidated sessions to consolidate. Default: 3.

**Response:**
```json
{
  "summary_ids": [1, 2],
  "session_window": 3,
  "consolidated_memory_count": 15,
  "session_count": 3,
  "summary_count": 2,
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8080/api/v1/consolidate" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-123",
    "window_size": 3
  }'
```

---

### GET /api/v1/consolidate/stats

Get consolidation statistics for a user.

**Query Parameters:**
- `user_id` (string, required): User identifier

**Response:**
```json
{
  "unconsolidated_sessions": 5,
  "consolidated_sessions": 10,
  "total_summaries": 3,
  "ready_for_consolidation": true
}
```

**Example:**
```bash
curl "http://localhost:8080/api/v1/consolidate/stats?user_id=user-123"
```

---

## Notes

- All endpoints return JSON responses
- All timestamps are in ISO 8601 format (UTC)
- UUIDs should be provided as strings
- Query parameters are case-sensitive
- Default port: 8080 (configurable via Docker Compose)
