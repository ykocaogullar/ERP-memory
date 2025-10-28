# Docker Setup for ERP Memory System

This document explains how to run the ERP Memory System using Docker containers.

## Quick Start

1. **Start the system:**
   ```bash
   ./start_docker.sh
   ```

2. **Access the API:**
   - API: http://localhost:8080
   - Health Check: http://localhost:8080/health
   - API Documentation: http://localhost:8080/docs

3. **Stop the system:**
   ```bash
   docker-compose down
   ```

## Architecture

The Docker setup includes 4 services:

### 1. Database (`erp_db`)
- **Image:** `pgvector/pgvector:pg15`
- **Purpose:** PostgreSQL database with pgvector extension
- **Port:** 5432
- **Credentials:** `erp_user` / `erp_password`
- **Database:** `erp_db`

### 2. Migrations (`erp_migrations`)
- **Image:** `postgres:15`
- **Purpose:** Runs database schema migrations
- **Dependencies:** Waits for database to be healthy
- **Action:** Executes `001_initial_schema.sql`

### 3. Seed Data (`erp_seed`)
- **Image:** `postgres:15`
- **Purpose:** Populates database with sample data
- **Dependencies:** Waits for migrations to complete
- **Action:** Executes `seed_data.sql`

### 4. API Server (`erp_api`)
- **Image:** Built from local `Dockerfile`
- **Purpose:** FastAPI application server
- **Port:** 8080
- **Dependencies:** Waits for seed data to complete
- **Features:** Auto-reload enabled for development

## Environment Variables

The API service uses these environment variables:

```bash
# Database Configuration
DATABASE_URL=postgresql://erp_user:erp_password@db:5432/erp_db
DB_HOST=db
DB_PORT=5432
DB_NAME=erp_db
DB_USER=erp_user
DB_PASSWORD=erp_password

# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Feature Flags
ENABLE_VECTORS=true
ENABLE_PII_REDACTION=true
ENABLE_SEMANTIC_RELATIONSHIPS=true
ENTITY_EMBEDDING_ENABLED=true

# Logging
LOG_LEVEL=INFO
```

## Docker Commands

### Basic Operations
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f

# Restart API only
docker-compose restart api
```

### Development Commands
```bash
# Rebuild API container
docker-compose build api

# Access API container shell
docker-compose exec api bash

# View database logs
docker-compose logs db

# Access database directly
docker-compose exec db psql -U erp_user -d erp_db
```

### Monitoring
```bash
# Check service status
docker-compose ps

# View resource usage
docker stats

# Check API health
curl http://localhost:8080/health
```

## Testing

Run the Docker integration tests:

```bash
python3 tests/test_docker_integration.py
```

This will test:
- ✅ Docker services are running
- ✅ API health check
- ✅ API endpoints functionality
- ✅ Database connectivity
- ✅ Chat endpoint with memory creation

## Troubleshooting

### Common Issues

1. **API can't connect to database:**
   - Check if `DB_HOST=db` is set in environment
   - Verify database container is healthy: `docker-compose ps`

2. **Port conflicts:**
   - Change ports in `docker-compose.yml` if 8080 or 5432 are in use
   - Update API_BASE_URL in test scripts

3. **Missing OpenAI API key:**
   - Set `OPENAI_API_KEY` environment variable
   - Or create `.env` file with your API key

4. **Container startup failures:**
   - Check logs: `docker-compose logs`
   - Verify all dependencies are installed
   - Try rebuilding: `docker-compose build --no-cache`

### Logs and Debugging

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs api
docker-compose logs db

# Follow logs in real-time
docker-compose logs -f api

# Check container status
docker-compose ps
```

## Production Considerations

For production deployment:

1. **Security:**
   - Use strong passwords
   - Enable SSL/TLS
   - Restrict network access
   - Use secrets management

2. **Performance:**
   - Increase database connection pool
   - Add Redis for caching
   - Use production WSGI server (Gunicorn)

3. **Monitoring:**
   - Add health checks
   - Set up logging aggregation
   - Monitor resource usage

4. **Backup:**
   - Regular database backups
   - Persistent volume management
   - Disaster recovery procedures

## File Structure

```
├── Dockerfile              # API container definition
├── docker-compose.yml      # Multi-service orchestration
├── .dockerignore          # Docker build exclusions
├── start_docker.sh        # Startup script
├── tests/
│   └── test_docker_integration.py  # Docker tests
└── api/                   # Application code
    ├── main.py           # FastAPI app
    ├── services/         # Business logic
    └── routes/           # API endpoints
```

