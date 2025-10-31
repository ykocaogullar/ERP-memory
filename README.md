# ERP Memory System

An ontology-aware memory system for LLM agents that persists and evolves memory across sessions, grounded in PostgreSQL business data.

## Features

- **Memory Persistence**: Stores episodic, semantic, and profile memories with vector embeddings
- **Entity Linking**: Automatically extracts and links business entities (customers, orders, invoices)
- **Semantic Relationships**: Builds relationships between entities from conversations
- **Business Context**: Retrieves real-time business data to enhance LLM responses

## Quick Start

### Prerequisites
- Docker and Docker Compose
- OpenAI API key

### Setup

```bash
# Set your OpenAI API key
export OPENAI_API_KEY=sk-your-actual-key-here

# Start all services
docker-compose up -d

# Verify
curl http://localhost:8080/health

# Run demo
cd demo && bash demo.sh
```

## API Usage

Main chat endpoint:

```bash
curl -X POST http://localhost:8080/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the status of order SO-1001?",
    "user_id": "user-123",
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "create_memories": true,
    "max_memories": 10
  }'
```

Other endpoints:
- `GET /health` - Health check
- `GET /stats` - System statistics
- `POST /api/v1/memory/query` - Query memories
- `POST /api/v1/entities/search` - Search entities
- `POST /api/v1/consolidate` - Consolidate memories

See `docs/API_SPEC.md` for complete API documentation.

## Configuration

Key environment variables:
- `OPENAI_API_KEY` (required) - OpenAI API key
- `ENABLE_VECTORS` - Enable vector embeddings (default: `true`)
- `ENABLE_SEMANTIC_RELATIONSHIPS` - Enable relationships (default: `true`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

## Project Structure

```
├── api/           # FastAPI application
│   ├── routes/    # API endpoints
│   ├── services/  # Business logic
│   └── models/    # Data models
├── db/            # Database migrations and seeds
├── demo/          # Demo scripts
└── docs/          # Documentation
```

## Development

```bash
# Local development
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start database
docker-compose up -d db

# Run API locally
uvicorn api.main:app --reload --host 0.0.0.0 --port 8080
```

## Logs

- API logs: `docker-compose logs -f api`
- Demo logs: `demo/retrieval_synthesis.log` and `demo/llm_prompts.log`

## Reset System

To purge all memories:

```bash
cd demo && bash reset_system.sh
```

---

**Note**: This is a proof-of-concept system for demonstration purposes.
