# ERP Memory System - Docker Setup

## Quick Start

1. **Set your OpenAI API key:**
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. **Start the system:**
   ```bash
   docker-compose up -d
   ```

3. **Check status:**
   ```bash
   docker-compose ps
   ```

4. **Access the API:**
   - API: http://localhost:8080
   - Health: http://localhost:8080/health
   - Docs: http://localhost:8080/docs

5. **Stop the system:**
   ```bash
   docker-compose down
   ```

## What Happens When You Run `docker-compose up -d`

1. **Database** (`erp_db`) starts first
2. **Migrations** (`erp_migrations`) runs after database is healthy
3. **Seed** (`erp_seed`) runs after migrations complete
4. **API** (`erp_api`) starts after seed completes and includes health checks

## Useful Commands

```bash
# View logs
docker-compose logs -f

# Restart API only
docker-compose restart api

# Rebuild and restart
docker-compose up --build -d

# Access API container
docker-compose exec api bash

# Check API health
curl http://localhost:8080/health
```

## Environment Variables

Required:
- `OPENAI_API_KEY`: Your OpenAI API key

Optional (with defaults):
- `ENABLE_VECTORS=true`
- `ENABLE_PII_REDACTION=true`
- `ENABLE_SEMANTIC_RELATIONSHIPS=true`
- `ENTITY_EMBEDDING_ENABLED=true`
- `LOG_LEVEL=INFO`

## Testing

Run the integration tests:
```bash
python3 tests/test_docker_integration.py
```
