# ERP Memory System - Setup Guide

## Overview

This is an ontology-aware memory system for LLM agents that persists and evolves memory across sessions, grounded in data from a PostgreSQL database representing basic business processes.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.12+ (for local development)
- OpenAI API key

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd ERP-memory

# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-actual-key-here
```

### 2. Start Database and Load Schema

```bash
# Start PostgreSQL database with pgvector extension
sudo docker-compose up -d db

# Wait for database to be ready (about 5 seconds)
sleep 5

# Run migrations to create schema
sudo docker-compose up migrations

# Load seed data
sudo docker-compose up seed
```

### 3. Verify Database Setup

```bash
# Connect to database
sudo docker exec -it erp_db psql -U erp_user -d erp_db

# Check tables
\dt domain.*
\dt app.*

# View sample data
SELECT name, industry FROM domain.customers;

# Exit
\q
```

Or run the Python test:

```bash
source .venv/bin/activate  # or source venv/bin/activate
python test_db_connection.py
```

### 4. Start API Service (Coming Soon)

```bash
sudo docker-compose up -d api
```

## Database Schema

### Domain Schema (ERP Data)

The `domain` schema contains business process data:

- **customers** - Customer information (name, industry, notes)
- **sales_orders** - Sales orders linked to customers
- **work_orders** - Work orders linked to sales orders
- **invoices** - Invoices linked to sales orders
- **payments** - Payments linked to invoices
- **tasks** - Support tasks linked to customers

### App Schema (Memory System)

The `app` schema contains the memory system:

- **chat_events** - Raw conversation messages
- **entities** - Extracted entities with optional embeddings
- **entity_aliases** - Entity name variations and mappings
- **entity_relationships** - Semantic triples (subject, predicate, object)
- **memories** - Vectorized memory chunks (episodic, semantic, etc.)
- **memory_summaries** - Consolidated cross-session summaries
- **sessions** - Session metadata

## Seed Data

The system comes with sample data:

- **3 Customers**: Gai Media (Entertainment), PC Boiler (Industrial), TC Boiler (Industrial)
- **2 Sales Orders**: SO-1001 (Album Fulfillment), SO-2002 (Valve Repair)
- **2 Work Orders**: One queued, one blocked
- **2 Invoices**: INV-1009 ($1,200, open), INV-2201 ($850, open)
- **1 Partial Payment**: $400 on INV-2201
- **2 Support Tasks**: SLA investigation, repair follow-up

## Extensions Enabled

- **pgvector** (v0.8.1) - Vector similarity search for embeddings
- **pg_trgm** (v1.6) - Trigram-based fuzzy text matching

## Useful Commands

### Docker Management

```bash
# View running containers
sudo docker-compose ps

# View logs
sudo docker-compose logs db
sudo docker-compose logs -f api  # Follow logs

# Stop all services
sudo docker-compose down

# Stop and remove volumes (DELETES DATA)
sudo docker-compose down -v

# Restart a service
sudo docker-compose restart db
```

### Database Access

```bash
# Connect to database
sudo docker exec -it erp_db psql -U erp_user -d erp_db

# Run a query from command line
sudo docker exec -it erp_db psql -U erp_user -d erp_db -c "SELECT * FROM domain.customers;"

# Backup database
sudo docker exec erp_db pg_dump -U erp_user erp_db > backup.sql

# Restore database
cat backup.sql | sudo docker exec -i erp_db psql -U erp_user -d erp_db
```

## Python Development

### Setup Virtual Environment

```bash
# Create virtual environment
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running Tests

```bash
source .venv/bin/activate
python test_db_connection.py
```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  FastAPI API                    │
│  /chat  /memory  /consolidate  /entities       │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│           Memory System Services                │
│  - Entity Extraction                            │
│  - Semantic Relationships                       │
│  - Vector Embeddings                            │
│  - Memory Storage & Retrieval                   │
│  - Consolidation                                │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│        PostgreSQL + pgvector                    │
│                                                 │
│  ┌──────────────┐    ┌──────────────┐          │
│  │ Domain Schema│    │  App Schema  │          │
│  │ (ERP Data)   │    │ (Memories)   │          │
│  └──────────────┘    └──────────────┘          │
└─────────────────────────────────────────────────┘
```

## Troubleshooting

### Database won't start

```bash
# Check logs
sudo docker-compose logs db

# Clean restart
sudo docker-compose down -v
sudo docker-compose up -d db
```

### Migrations fail

```bash
# Check if database is ready
sudo docker exec erp_db pg_isready -U erp_user

# Manually run migrations
sudo docker-compose up migrations
```

### Permission denied errors

If you get "permission denied" when running docker commands:

```bash
# Add yourself to docker group (then log out and back in)
sudo usermod -aG docker $USER

# Or use sudo for docker commands
sudo docker-compose up -d
```

## Environment Variables

Key configuration options in `.env`:

```bash
# Database
DB_NAME=erp_db
DB_USER=erp_user
DB_PASSWORD=erp_password

# OpenAI
OPENAI_API_KEY=sk-your-key-here

# Memory System
ENABLE_VECTORS=true
ENABLE_PII_REDACTION=true
TRIGRAM_THRESHOLD=0.3
MEMORY_TTL_DAYS=30
CONSOLIDATION_WINDOW=3
VECTOR_DIMENSIONS=1536

# Semantic Layer
ENABLE_SEMANTIC_RELATIONSHIPS=true
ENTITY_EMBEDDING_ENABLED=true
SEMANTIC_SCORE_WEIGHT=0.2
```

## Development Setup

### Install Python Dependencies

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Verify Installation

```bash
# Activate virtual environment
source .venv/bin/activate

# Run core component tests
python tests/test_core_components.py
```

Expected output:
- ✅ Configuration loads correctly
- ✅ Database connection works
- ✅ All models validate
- ✅ Embedding service functional

---

## Next Steps

After setup is complete:

1. **Explore the architecture**: See `docs/ARCHITECTURE.md` for system design and components
2. **Review the database schema**: Connect to database and explore tables
3. **Check implementation plan**: `documents/IMPLEMENTATION_PLAN.md` for development roadmap
4. **Start developing**: Continue with Phase 4 - Entity Linking & Semantic Layer

---

## Support

For issues or questions, refer to:
- Architecture documentation: `docs/ARCHITECTURE.md`
- Implementation Plan: `documents/IMPLEMENTATION_PLAN.md`
- Original Assignment: `documents/Take‑Home Ontology-Aware Memory System for an LLM.md`
