-- Enable extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Domain schema (ERP data)
CREATE SCHEMA IF NOT EXISTS domain;

-- Customers
CREATE TABLE domain.customers (
    customer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    industry TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Sales Orders
CREATE TABLE domain.sales_orders (
    so_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID NOT NULL REFERENCES domain.customers(customer_id),
    so_number TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('draft','approved','in_fulfillment','fulfilled','cancelled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Work Orders
CREATE TABLE domain.work_orders (
    wo_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    so_id UUID NOT NULL REFERENCES domain.sales_orders(so_id),
    description TEXT,
    status TEXT NOT NULL CHECK (status IN ('queued','in_progress','blocked','done')),
    technician TEXT,
    scheduled_for DATE
);

-- Invoices
CREATE TABLE domain.invoices (
    invoice_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    so_id UUID NOT NULL REFERENCES domain.sales_orders(so_id),
    invoice_number TEXT UNIQUE NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    due_date DATE NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('open','paid','void')),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Payments
CREATE TABLE domain.payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES domain.invoices(invoice_id),
    amount NUMERIC(12,2) NOT NULL,
    method TEXT,
    paid_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Tasks
CREATE TABLE domain.tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_id UUID REFERENCES domain.customers(customer_id),
    title TEXT NOT NULL,
    body TEXT,
    status TEXT NOT NULL CHECK (status IN ('todo','doing','done')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- App schema (Memory system)
CREATE SCHEMA IF NOT EXISTS app;

-- Chat events
CREATE TABLE app.chat_events (
    event_id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user','assistant','system')),
    content TEXT NOT NULL,
    content_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chat_events_session ON app.chat_events(session_id);
CREATE INDEX idx_chat_events_hash ON app.chat_events(content_hash);
CREATE INDEX idx_chat_events_user ON app.chat_events(user_id);

-- Entities (enhanced with embeddings)
CREATE TABLE app.entities (
    entity_id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    name_hash TEXT NOT NULL,
    canonical_name TEXT,
    type TEXT NOT NULL, -- customer, order, invoice, person, topic
    source TEXT NOT NULL CHECK (source IN ('message','db','alias')),
    external_ref JSONB,
    confidence REAL DEFAULT 1.0,
    entity_embedding vector(1536), -- Entity-level embedding
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_entities_hash ON app.entities(name_hash);
CREATE INDEX idx_entities_canonical ON app.entities(canonical_name);
CREATE INDEX idx_entities_user ON app.entities(user_id);
CREATE INDEX idx_entities_embedding ON app.entities 
    USING ivfflat (entity_embedding vector_cosine_ops)
    WHERE entity_embedding IS NOT NULL;

-- Entity aliases
CREATE TABLE app.entity_aliases (
    alias_id BIGSERIAL PRIMARY KEY,
    canonical_entity_id BIGINT NOT NULL,
    alias_text TEXT NOT NULL,
    alias_hash TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('user_correction','fuzzy_match','multilingual')),
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(alias_hash, canonical_entity_id)
);

CREATE INDEX idx_aliases_hash ON app.entity_aliases(alias_hash);

-- Entity relationships (semantic triples)
CREATE TABLE app.entity_relationships (
    relationship_id BIGSERIAL PRIMARY KEY,
    subject_entity_id BIGINT NOT NULL,
    predicate TEXT NOT NULL, -- e.g., 'issued_to', 'delivered_by', 'prefers'
    object_entity_id BIGINT,
    object_value TEXT, -- for non-entity objects
    relationship_embedding vector(1536), -- embedding of the triple
    confidence REAL DEFAULT 1.0,
    source TEXT NOT NULL CHECK (source IN ('db_schema','conversation','inference')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_relationships_subject ON app.entity_relationships(subject_entity_id);
CREATE INDEX idx_relationships_predicate ON app.entity_relationships(predicate);
CREATE INDEX idx_relationships_embedding ON app.entity_relationships
    USING ivfflat (relationship_embedding vector_cosine_ops)
    WHERE relationship_embedding IS NOT NULL;

-- Memories
CREATE TABLE app.memories (
    memory_id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('episodic','semantic','profile','policy','commitment','todo')),
    text TEXT NOT NULL,
    embedding vector(1536),
    importance REAL NOT NULL DEFAULT 0.5,
    ttl_days INT,
    expires_at TIMESTAMPTZ,
    provenance JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX idx_memories_session ON app.memories(session_id);
CREATE INDEX idx_memories_user ON app.memories(user_id);
CREATE INDEX idx_memories_kind ON app.memories(kind);
CREATE INDEX idx_memories_expires ON app.memories(expires_at)
    WHERE expires_at IS NOT NULL;
CREATE INDEX idx_memories_embedding ON app.memories
    USING ivfflat (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;
CREATE INDEX idx_memories_fts ON app.memories
    USING gin(to_tsvector('english', text));
CREATE INDEX idx_memories_trigram ON app.memories
    USING gin(text gin_trgm_ops);
CREATE INDEX idx_memories_provenance ON app.memories
    USING gin(provenance);

-- Memory summaries
CREATE TABLE app.memory_summaries (
    summary_id BIGSERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_window INT NOT NULL,
    summary TEXT NOT NULL,
    embedding vector(1536),
    consolidated_memory_ids BIGINT[],
    importance REAL DEFAULT 0.7,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_summaries_user ON app.memory_summaries(user_id);
CREATE INDEX idx_summaries_embedding ON app.memory_summaries
    USING ivfflat (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

-- Sessions
CREATE TABLE app.sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    turn_count INT DEFAULT 0,
    consolidated BOOLEAN DEFAULT false
);

CREATE INDEX idx_sessions_user ON app.sessions(user_id);
CREATE INDEX idx_sessions_activity ON app.sessions(last_activity_at);
