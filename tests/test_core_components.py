"""
Phase 3 Integration Tests

Tests all components built in Phase 3:
- Configuration
- Database connectivity
- Domain models
- Memory models
- API models
- Embedding service
"""

import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.utils.config import settings
from api.utils.database import db
from api.models import (
    Customer, SalesOrder, Invoice,
    Entity, Memory, Session, SemanticTriple,
    ChatRequest, ChatMessage, ChatResponse,
    EntityKind, MemoryKind, OrderStatus, InvoiceStatus
)
from api.services import get_embedding_service


def test_configuration():
    """Test configuration loads correctly"""
    print("\n" + "="*60)
    print("TEST 1: Configuration")
    print("="*60)
    
    assert settings.DB_NAME == "erp_db", "Database name mismatch"
    assert settings.DB_HOST == "localhost", "Database host mismatch"
    assert settings.OPENAI_API_KEY.startswith("sk-"), "Invalid OpenAI API key format"
    assert settings.EMBEDDING_MODEL == "text-embedding-3-small", "Wrong embedding model"
    assert settings.EMBEDDING_DIMENSION == 1536, "Wrong embedding dimension"
    
    print("✅ Configuration loaded successfully")
    print(f"   - Database: {settings.DB_NAME}")
    print(f"   - Embedding Model: {settings.EMBEDDING_MODEL}")
    print(f"   - Dimension: {settings.EMBEDDING_DIMENSION}")
    print(f"   - API Key: {settings.OPENAI_API_KEY[:20]}...")
    

def test_database_connection():
    """Test database connectivity and queries"""
    print("\n" + "="*60)
    print("TEST 2: Database Connection")
    print("="*60)
    
    # Test basic query
    result = db.execute_query("SELECT current_database(), version()", fetch_one=True)
    print(f"✅ Connected to: {result['current_database']}")
    print(f"   PostgreSQL version: {result['version'][:50]}...")
    
    # Test extensions
    extensions = db.execute_query(
        "SELECT extname FROM pg_extension WHERE extname IN ('vector', 'pg_trgm')",
        fetch_one=False
    )
    ext_names = [e['extname'] for e in extensions]
    assert 'vector' in ext_names, "pgvector extension not installed"
    assert 'pg_trgm' in ext_names, "pg_trgm extension not installed"
    print(f"✅ Extensions installed: {', '.join(ext_names)}")
    
    # Test schemas
    schemas = db.execute_query(
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('domain', 'app')",
        fetch_one=False
    )
    schema_names = [s['schema_name'] for s in schemas]
    assert 'domain' in schema_names, "Domain schema missing"
    assert 'app' in schema_names, "App schema missing"
    print(f"✅ Schemas present: {', '.join(schema_names)}")


def test_domain_models():
    """Test domain models with real database data"""
    print("\n" + "="*60)
    print("TEST 3: Domain Models")
    print("="*60)
    
    # Test Customer model
    customer_row = db.execute_query(
        "SELECT * FROM domain.customers ORDER BY name LIMIT 1",
        fetch_one=True
    )
    customer = Customer(**customer_row)
    print(f"✅ Customer model: {customer.name} ({customer.industry})")
    assert customer.customer_id is not None
    assert isinstance(customer.created_at, datetime)
    
    # Test SalesOrder model
    order_row = db.execute_query(
        "SELECT * FROM domain.sales_orders ORDER BY created_at LIMIT 1",
        fetch_one=True
    )
    order = SalesOrder(**order_row)
    print(f"✅ SalesOrder model: {order.so_number} - {order.title}")
    assert order.status in OrderStatus.__members__.values()
    
    # Test Invoice model
    invoice_row = db.execute_query(
        "SELECT * FROM domain.invoices ORDER BY issued_at LIMIT 1",
        fetch_one=True
    )
    invoice = Invoice(**invoice_row)
    print(f"✅ Invoice model: {invoice.invoice_number} - Status: {invoice.status}")
    assert invoice.status in InvoiceStatus.__members__.values()
    assert invoice.amount > 0
    
    # Count all domain tables
    counts = db.execute_query("""
        SELECT 
            (SELECT COUNT(*) FROM domain.customers) as customers,
            (SELECT COUNT(*) FROM domain.sales_orders) as orders,
            (SELECT COUNT(*) FROM domain.invoices) as invoices,
            (SELECT COUNT(*) FROM domain.work_orders) as work_orders,
            (SELECT COUNT(*) FROM domain.payments) as payments,
            (SELECT COUNT(*) FROM domain.tasks) as tasks
    """, fetch_one=True)
    
    print(f"✅ Domain data counts:")
    for table, count in counts.items():
        print(f"   - {table}: {count}")


def test_memory_models():
    """Test memory models structure"""
    print("\n" + "="*60)
    print("TEST 4: Memory Models")
    print("="*60)
    
    # Test Entity model
    entity = Entity(
        entity_id=uuid4(),
        kind=EntityKind.CUSTOMER,
        name="Test Customer",
        canonical_name="test_customer",
        domain_id=uuid4(),
        attributes={"industry": "Technology"},
        embedding=[0.1] * 1536,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    print(f"✅ Entity model: {entity.name} ({entity.kind})")
    assert len(entity.embedding) == 1536
    assert entity.kind == EntityKind.CUSTOMER
    
    # Test Memory model
    memory = Memory(
        memory_id=uuid4(),
        session_id=uuid4(),
        content="Customer asked about order status",
        kind=MemoryKind.CONVERSATION,
        importance=0.7,
        embedding=[0.2] * 1536,
        metadata={"user_id": "test_user"},
        created_at=datetime.now(),
        updated_at=datetime.now(),
        accessed_at=datetime.now(),
        access_count=0
    )
    print(f"✅ Memory model: '{memory.content[:40]}...' (importance: {memory.importance})")
    assert memory.importance >= 0.0 and memory.importance <= 1.0
    assert memory.kind == MemoryKind.CONVERSATION
    
    # Test Session model
    session = Session(
        session_id=uuid4(),
        user_id="test_user",
        started_at=datetime.now(),
        metadata={"source": "test"}
    )
    print(f"✅ Session model: {session.user_id}")
    
    # Test SemanticTriple model
    triple = SemanticTriple(
        triple_id=uuid4(),
        subject_entity_id=uuid4(),
        predicate="has_industry",
        object_value="Technology",
        confidence=0.95,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    print(f"✅ SemanticTriple model: {triple.predicate} = {triple.object_value}")
    assert triple.confidence >= 0.0 and triple.confidence <= 1.0
    
    print(f"✅ All memory models validated")


def test_api_models():
    """Test API request/response models"""
    print("\n" + "="*60)
    print("TEST 5: API Models")
    print("="*60)
    
    # Test ChatRequest
    chat_request = ChatRequest(
        messages=[
            ChatMessage(role="user", content="What is the status of my order?")
        ],
        session_id=uuid4(),
        user_id="test_user",
        max_tokens=1000,
        temperature=0.7,
        retrieve_memories=True,
        max_memories=10
    )
    print(f"✅ ChatRequest model: {len(chat_request.messages)} messages")
    assert chat_request.temperature >= 0.0 and chat_request.temperature <= 2.0
    assert chat_request.max_memories >= 1 and chat_request.max_memories <= 50
    
    # Test ChatResponse
    chat_response = ChatResponse(
        response="Your order is in progress",
        session_id=uuid4(),
        memories_created=2,
        entities_linked=3
    )
    print(f"✅ ChatResponse model: '{chat_response.response}'")
    assert chat_response.memories_created >= 0
    assert chat_response.entities_linked >= 0
    
    print(f"✅ All API models validated")


def test_embedding_service():
    """Test embedding service"""
    print("\n" + "="*60)
    print("TEST 6: Embedding Service")
    print("="*60)
    
    service = get_embedding_service()
    
    # Test single embedding
    text1 = "What is the status of order ORD-2024-001?"
    embedding1 = service.embed_text(text1)
    print(f"✅ Single embedding generated")
    print(f"   - Text: '{text1}'")
    print(f"   - Dimension: {len(embedding1)}")
    print(f"   - First 5 values: {embedding1[:5]}")
    assert len(embedding1) == 1536
    assert all(isinstance(x, float) for x in embedding1)
    
    # Test batch embedding
    texts = [
        "Customer Gai Media in entertainment industry",
        "Sales order ORD-2024-001 for $50,000",
        "Invoice INV-2024-001 paid in full"
    ]
    batch_embeddings = service.embed_batch(texts)
    print(f"\n✅ Batch embedding generated")
    print(f"   - Texts: {len(texts)}")
    print(f"   - Embeddings: {len(batch_embeddings)}")
    assert len(batch_embeddings) == len(texts)
    assert all(len(e) == 1536 for e in batch_embeddings)
    
    # Test cosine similarity
    sim_same = service.cosine_similarity(batch_embeddings[0], batch_embeddings[0])
    sim_diff = service.cosine_similarity(batch_embeddings[0], batch_embeddings[1])
    print(f"\n✅ Cosine similarity calculated")
    print(f"   - Same text: {sim_same:.4f} (should be ~1.0)")
    print(f"   - Different text: {sim_diff:.4f} (should be < 1.0)")
    assert sim_same > 0.99  # Should be very close to 1.0
    assert sim_diff < sim_same  # Different texts less similar
    
    # Test caching
    text_cached = "Test caching"
    emb1 = service.embed_text(text_cached, use_cache=True)
    emb2 = service.embed_text(text_cached, use_cache=True)  # Should use cache
    print(f"\n✅ Caching tested")
    print(f"   - Cache enabled: True")
    print(f"   - Results identical: {list(emb1) == list(emb2)}")
    assert list(emb1) == list(emb2)


def test_database_operations():
    """Test actual database operations with memory tables"""
    print("\n" + "="*60)
    print("TEST 7: Database Operations (Memory Tables)")
    print("="*60)
    
    # Check if memory tables exist and are empty or have data
    memory_counts = db.execute_query("""
        SELECT 
            (SELECT COUNT(*) FROM app.entities) as entities,
            (SELECT COUNT(*) FROM app.memories) as memories,
            (SELECT COUNT(*) FROM app.sessions) as sessions,
            (SELECT COUNT(*) FROM app.chat_events) as chat_events,
            (SELECT COUNT(*) FROM app.entity_relationships) as relationships,
            (SELECT COUNT(*) FROM app.entity_aliases) as aliases,
            (SELECT COUNT(*) FROM app.memory_summaries) as summaries
    """, fetch_one=True)
    
    print(f"✅ Memory tables exist and are queryable:")
    for table, count in memory_counts.items():
        print(f"   - {table}: {count} records")
    
    # Test vector column exists
    vector_col = db.execute_query("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'app' 
        AND table_name = 'memories' 
        AND column_name = 'embedding'
    """, fetch_one=True)
    
    assert vector_col is not None, "Embedding column not found in memories table"
    print(f"✅ Vector column exists: app.memories.embedding ({vector_col['data_type']})")
    
    # Test indexes
    indexes = db.execute_query("""
        SELECT indexname 
        FROM pg_indexes 
        WHERE schemaname = 'app' 
        AND indexname LIKE '%embedding%'
    """, fetch_one=False)
    
    index_names = [idx['indexname'] for idx in indexes]
    print(f"✅ Vector indexes found: {len(index_names)}")
    for idx_name in index_names:
        print(f"   - {idx_name}")


def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "="*70)
    print(" "*15 + "PHASE 3 INTEGRATION TEST SUITE")
    print("="*70)
    
    try:
        test_configuration()
        test_database_connection()
        test_domain_models()
        test_memory_models()
        test_api_models()
        test_embedding_service()
        test_database_operations()
        
        print("\n" + "="*70)
        print("✅ " + " "*20 + "ALL TESTS PASSED!")
        print("="*70)
        print("="*70 + "\n")
        
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
