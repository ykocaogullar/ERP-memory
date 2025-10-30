"""
Test Phase 5: Memory System Implementation

Tests the complete memory system workflow including:
- Memory vectorization
- Memory storage with PII redaction
- Retrieval and synthesis
- Prompt building
- LLM integration
"""

import pytest
import json
from datetime import datetime, date
from unittest.mock import patch, MagicMock

from api.services.memory_vectorizer import get_memory_vectorizer
from api.services.memory_storage import get_memory_storage
from api.services.retrieval_synthesis import get_retrieval_synthesis
from api.services.prompt_builder import get_prompt_builder
from api.services.llm_service import get_llm_service


class TestMemoryVectorizer:
    """Test memory vectorization functionality"""
    
    def test_extract_episodic_memory(self):
        """Test episodic memory extraction"""
        vectorizer = get_memory_vectorizer()
        
        user_message = "Check status of SO-1001 for Gai Media"
        assistant_message = "SO-1001 is currently in_fulfillment status"
        entities = [
            {'name': 'SO-1001', 'type': 'sales_order', 'confidence': 1.0},
            {'name': 'Gai Media', 'type': 'customer', 'confidence': 0.8}
        ]
        
        memories = vectorizer.analyze_conversation_turn(
            user_message, assistant_message, entities, 'test-session', 'test-user'
        )
        
        assert len(memories) > 0
        
        # Check for episodic memory
        episodic_memories = [m for m in memories if m['kind'] == 'episodic']
        assert len(episodic_memories) == 1
        
        episodic = episodic_memories[0]
        assert 'SO-1001' in episodic['text']
        assert 'Gai Media' in episodic['text']
        assert episodic['importance'] > 0
        assert episodic['ttl_days'] == 30
    
    def test_extract_semantic_memories(self):
        """Test semantic memory extraction"""
        vectorizer = get_memory_vectorizer()
        
        user_message = "Gai Media prefers Friday deliveries and requires NET30 payment terms"
        entities = [{'name': 'Gai Media', 'type': 'customer', 'confidence': 0.8}]
        
        memories = vectorizer.analyze_conversation_turn(
            user_message, "", entities, 'test-session', 'test-user'
        )
        
        # Should extract preference and requirement memories
        preference_memories = [m for m in memories if 'prefer' in m['text'].lower()]
        requirement_memories = [m for m in memories if 'require' in m['text'].lower()]
        
        assert len(preference_memories) > 0
        assert len(requirement_memories) > 0
        
        # Check that we have semantic memories (may also have episodic)
        semantic_memories = [m for m in memories if m['kind'] == 'semantic']
        assert len(semantic_memories) > 0
        
        # Check memory structure for semantic memories
        for memory in semantic_memories:
            assert memory['kind'] == 'semantic'
            assert memory['ttl_days'] is None  # Semantic memories don't expire
            assert memory['importance'] > 0
    
    def test_extract_commitment_memories(self):
        """Test commitment memory extraction"""
        vectorizer = get_memory_vectorizer()
        
        user_message = "I will follow up on the invoice payment next week"
        entities = []
        
        memories = vectorizer.analyze_conversation_turn(
            user_message, "", entities, 'test-session', 'test-user'
        )
        
        commitment_memories = [m for m in memories if m['kind'] == 'commitment']
        assert len(commitment_memories) > 0
        
        commitment = commitment_memories[0]
        assert 'follow up' in commitment['text'].lower()
        assert commitment['importance'] > 0.8  # Commitments are high importance
        assert commitment['ttl_days'] == 90
    
    def test_extract_todo_memories(self):
        """Test todo memory extraction"""
        vectorizer = get_memory_vectorizer()
        
        user_message = "Need to check invoice status for Riverbend Fabrication"
        assistant_message = "I'll add that to the todo list"
        entities = [{'name': 'Riverbend Fabrication', 'type': 'customer', 'confidence': 0.9}]
        
        memories = vectorizer.analyze_conversation_turn(
            user_message, assistant_message, entities, 'test-session', 'test-user'
        )
        
        todo_memories = [m for m in memories if m['kind'] == 'todo']
        assert len(todo_memories) > 0
        
        todo = todo_memories[0]
        assert 'Riverbend Fabrication' in todo['text']
        assert todo['ttl_days'] == 14
    
    def test_consolidate_memories(self):
        """Test memory consolidation"""
        vectorizer = get_memory_vectorizer()
        
        memories = [
            {
                'kind': 'semantic',
                'text': 'Gai Media prefers Friday deliveries',
                'importance': 0.8,
                'provenance': {'entities': ['Gai Media']}
            },
            {
                'kind': 'semantic',
                'text': 'Gai Media prefers Friday deliveries',
                'importance': 0.7,
                'provenance': {'entities': ['Gai Media']}
            }
        ]
        
        consolidated = vectorizer.consolidate_memories(memories, 'test-user')
        
        assert len(consolidated) == 1
        assert consolidated[0]['importance'] >= 0.8  # Should keep higher importance


class TestMemoryStorage:
    """Test memory storage functionality"""
    
    def test_redact_pii(self):
        """Test PII redaction"""
        storage = get_memory_storage()
        
        memory = {
            'text': 'Contact john@example.com at 555-123-4567 for payment',
            'kind': 'semantic',
            'importance': 0.8
        }
        
        redacted = storage._redact_pii(memory)
        
        assert '[EMAIL]' in redacted['text']
        assert '[PHONE]' in redacted['text']
        assert 'john@example.com' not in redacted['text']
        assert '555-123-4567' not in redacted['text']
        
        # Check PII tracking
        assert 'pii_redacted' in redacted['provenance']
    
    def test_create_content_hash(self):
        """Test content hashing for deduplication"""
        storage = get_memory_storage()
        
        text1 = "Gai Media prefers Friday deliveries"
        text2 = "Gai Media prefers Friday deliveries"
        text3 = "Gai Media prefers Monday deliveries"
        
        hash1 = storage._create_content_hash(text1)
        hash2 = storage._create_content_hash(text2)
        hash3 = storage._create_content_hash(text3)
        
        assert hash1 == hash2  # Same content should have same hash
        assert hash1 != hash3  # Different content should have different hash
    
    @patch('api.services.memory_storage.db.execute_query')
    @patch('api.services.memory_storage.db.get_connection')
    def test_store_memories(self, mock_connection, mock_query):
        """Test memory storage in database"""
        storage = get_memory_storage()
        
        # Mock database responses
        mock_query.side_effect = [
            [],  # No recent hashes
            None,  # Update content_hash call 1
            None,  # Update content_hash call 2
        ]
        
        # Mock connection and cursor with proper psycopg2 attributes
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        # Mock psycopg2 connection attributes
        mock_conn.encoding = 'utf-8'
        mock_cursor.connection = mock_conn
        
        # Mock execute_values result
        mock_cursor.execute.return_value = None
        mock_cursor.rowcount = 2
        
        # Mock the execute_values function to return memory IDs
        with patch('psycopg2.extras.execute_values') as mock_execute_values:
            mock_execute_values.return_value = [(1,), (2,)]
            
            memories = [
                {
                    'kind': 'semantic',
                    'text': 'Gai Media prefers Friday deliveries',
                    'importance': 0.8,
                    'ttl_days': None
                },
                {
                    'kind': 'commitment',
                    'text': 'Will follow up next week',
                    'importance': 0.9,
                    'ttl_days': 90
                }
            ]
            
            memory_ids = storage.store_memories(memories, 'test-session', 'test-user')
            
            assert len(memory_ids) == 2
    
    @patch('api.services.memory_storage.db.execute_query')
    def test_get_memories(self, mock_query):
        """Test memory retrieval"""
        storage = get_memory_storage()
        
        # Mock database response
        mock_memories = [
            {
                'memory_id': 1,
                'kind': 'semantic',
                'text': 'Gai Media prefers Friday deliveries',
                'importance': 0.8,
                'created_at': datetime.now(),
                'expires_at': None,
                'provenance': '{}'
            }
        ]
        mock_query.return_value = mock_memories
        
        memories = storage.get_memories('test-user', limit=10)
        
        assert len(memories) == 1
        assert memories[0]['kind'] == 'semantic'
        assert memories[0]['text'] == 'Gai Media prefers Friday deliveries'


class TestRetrievalSynthesis:
    """Test retrieval and synthesis functionality"""
    
    @patch('api.services.retrieval_synthesis.db.execute_query')
    def test_hybrid_search(self, mock_query):
        """Test hybrid search combining multiple methods"""
        retrieval = get_retrieval_synthesis()
        
        # Mock database responses for different search methods
        mock_query.side_effect = [
            [],  # Vector search
            [],  # Full-text search
            [],  # Trigram search
            []   # Entity search
        ]
        
        query = "Gai Media delivery preferences"
        entities = [{'name': 'Gai Media', 'type': 'customer', 'confidence': 0.8}]
        
        memories = retrieval._hybrid_search(query, 'test-user', entities, 10)
        
        # Should return empty list due to mocked empty results
        assert isinstance(memories, list)
    
    @patch('api.services.retrieval_synthesis.get_domain_query_service')
    @patch('api.services.domain_queries.db.execute_query')
    def test_get_business_context(self, mock_db_query, mock_domain_service):
        """Test business context retrieval"""
        retrieval = get_retrieval_synthesis()
        
        # Mock database query to return customer data
        mock_db_query.return_value = {
            'customer_id': '123e4567-e89b-12d3-a456-426614174000',
            'name': 'Gai Media',
            'industry': 'Entertainment',
            'notes': 'Test customer',
            'created_at': '2025-01-01T00:00:00Z'
        }
        
        # Mock domain query service
        mock_service = MagicMock()
        mock_service.get_customer_data.return_value = {
            'customer': {'name': 'Gai Media', 'industry': 'Entertainment'},
            'orders': [{'so_number': 'SO-1001', 'status': 'in_fulfillment'}],
            'summary': {'total_orders': 1}
        }
        mock_domain_service.return_value = mock_service
        
        # Replace the domain_queries service in the retrieval object
        retrieval.domain_queries = mock_service
        
        entities = [{'name': 'Gai Media', 'type': 'customer', 'confidence': 0.8}]
        business_context = retrieval._get_business_context(entities)
        
        assert 'Gai Media' in business_context
        assert business_context['Gai Media']['customer']['name'] == 'Gai Media'
    
    def test_synthesize_context(self):
        """Test context synthesis"""
        retrieval = get_retrieval_synthesis()
        
        memories = [
            {
                'kind': 'semantic',
                'text': 'Gai Media: prefers Friday deliveries',
                'importance': 0.8,
                'created_at': datetime.now()
            }
        ]
        
        business_context = {
            'Gai Media': {
                'customer': {'name': 'Gai Media', 'industry': 'Entertainment'},
                'orders': [{'so_number': 'SO-1001', 'status': 'in_fulfillment'}]
            }
        }
        
        relationships = [
            {
                'subject': 'Gai Media',
                'predicate': 'prefers',
                'object': 'Friday deliveries',
                'confidence': 0.9,
                'source': 'conversation'
            }
        ]
        
        synthesized = retrieval._synthesize_context(
            memories, business_context, relationships, "test query"
        )
        
        assert 'memories' in synthesized
        assert 'business_context' in synthesized
        assert 'relationships' in synthesized
        assert 'semantic_triples' in synthesized
        assert 'summary' in synthesized
        assert 'metadata' in synthesized
        
        # Check semantic triples
        triples = synthesized['semantic_triples']
        assert len(triples) > 0
        
        # Should have memory triples and business triples
        memory_triples = [t for t in triples if t['source'] == 'memory']
        business_triples = [t for t in triples if t['source'] == 'business_data']
        
        assert len(memory_triples) > 0
        assert len(business_triples) > 0


class TestPromptBuilder:
    """Test prompt building functionality"""
    
    def test_build_prompt(self):
        """Test complete prompt building"""
        builder = get_prompt_builder()
        
        synthesized_context = {
            'memories': [
                {
                    'kind': 'semantic',
                    'text': 'Gai Media prefers Friday deliveries',
                    'importance': 0.8,
                    'created_at': datetime.now()
                }
            ],
            'business_context': {
                'Gai Media': {
                    'customer': {'name': 'Gai Media', 'industry': 'Entertainment'},
                    'orders': [{'so_number': 'SO-1001', 'status': 'in_fulfillment'}]
                }
            },
            'semantic_triples': [
                {
                    'subject': 'Gai Media',
                    'predicate': 'prefers',
                    'object': 'Friday deliveries',
                    'source': 'memory',
                    'confidence': 0.8
                }
            ]
        }
        
        prompt = builder.build_prompt("What are Gai Media's delivery preferences?", synthesized_context)
        
        assert "Gai Media's delivery preferences" in prompt
        assert "Business Context" in prompt
        assert "Relevant Memories" in prompt
        assert "Knowledge Graph" in prompt
        assert "Gai Media prefers Friday deliveries" in prompt
    
    def test_build_memory_prompt(self):
        """Test memory-focused prompt building"""
        builder = get_prompt_builder()
        
        memories = [
            {
                'kind': 'semantic',
                'text': 'Gai Media prefers Friday deliveries',
                'importance': 0.8,
                'created_at': datetime.now()
            }
        ]
        
        prompt = builder.build_memory_prompt("What are the delivery preferences?", memories)
        
        assert "Relevant Memories" in prompt
        assert "Gai Media prefers Friday deliveries" in prompt
        assert "What are the delivery preferences?" in prompt
    
    def test_format_semantic_triples(self):
        """Test semantic triples formatting"""
        builder = get_prompt_builder()
        
        triples = [
            {
                'subject': 'Gai Media',
                'predicate': 'prefers',
                'object': 'Friday deliveries',
                'confidence': 0.8
            },
            {
                'subject': 'SO-1001',
                'predicate': 'issued_to',
                'object': 'Gai Media',
                'confidence': 1.0
            }
        ]
        
        formatted = builder.format_semantic_triples(triples)
        
        assert "Gai Media prefers Friday deliveries" in formatted
        assert "SO-1001 issued_to Gai Media" in formatted
        assert "Confidence: 0.80" in formatted
        assert "Confidence: 1.00" in formatted


class TestLLMService:
    """Test LLM service functionality"""
    
    def test_fallback_response(self):
        """Test fallback response when LLM is not available"""
        llm = get_llm_service()
        
        # Mock the client to be None to trigger fallback
        llm.client = None
        
        prompt = "What are Gai Media's delivery preferences?"
        context = {
            'memories': [
                {
                    'kind': 'semantic',
                    'text': 'Gai Media prefers Friday deliveries',
                    'importance': 0.8
                }
            ],
            'business_context': {
                'Gai Media': {
                    'customer': {'name': 'Gai Media', 'industry': 'Entertainment'}
                }
            }
        }
        
        response = llm.generate_response(prompt, context)
        
        assert 'response' in response
        assert 'provider' in response
        assert 'usage' in response
        assert 'metadata' in response
        
        # Check fallback response content
        response_text = response['response']
        assert 'Gai Media' in response_text
        # The fallback response should contain either memories or business context
        assert ('memories' in response_text.lower() or 'business context' in response_text.lower())
    
    def test_generate_memory_summary(self):
        """Test memory summary generation"""
        llm = get_llm_service()
        
        memories = [
            {
                'kind': 'semantic',
                'text': 'Gai Media prefers Friday deliveries',
                'importance': 0.8
            },
            {
                'kind': 'commitment',
                'text': 'Will follow up next week',
                'importance': 0.9
            }
        ]
        
        summary = llm.generate_memory_summary(memories, 'test-user')
        
        assert 'Memory Summary for User test-user' in summary
        assert 'Semantic Memories' in summary
        assert 'Commitment Memories' in summary
        assert 'Gai Media prefers Friday deliveries' in summary
        assert 'Will follow up next week' in summary
    
    def test_extract_action_items(self):
        """Test action item extraction from response"""
        llm = get_llm_service()
        
        response = """
        Based on the information, I recommend:
        1. Action item: Follow up with Gai Media about their Friday delivery preference
        2. Todo: Check if SO-1001 can be delivered on Friday
        3. Next step: Confirm delivery schedule with logistics team
        """
        
        action_items = llm.extract_action_items(response)
        
        assert len(action_items) == 3
        assert 'Follow up with Gai Media' in action_items[0]['text']
        assert 'Check if SO-1001' in action_items[1]['text']
        assert 'Confirm delivery schedule' in action_items[2]['text']
        
        # Check action item structure
        for item in action_items:
            assert 'text' in item
            assert 'extracted_at' in item
            assert 'confidence' in item
    
    def test_validate_response(self):
        """Test response validation"""
        llm = get_llm_service()
        
        # Test valid response
        valid_response = "Based on the data, Gai Media prefers Friday deliveries. I recommend confirming this with the logistics team."
        validation = llm.validate_response(valid_response)
        
        assert validation['is_valid'] is True
        assert len(validation['issues']) == 0
        
        # Test invalid response
        invalid_response = "N/A"
        validation = llm.validate_response(invalid_response)
        
        assert validation['is_valid'] is False
        assert len(validation['issues']) > 0


class TestIntegration:
    """Test complete memory system integration"""
    
    @patch('api.services.memory_storage.db.execute_query')
    @patch('api.services.memory_storage.db.get_connection')
    @patch('api.services.retrieval_synthesis.db.execute_query')
    def test_complete_workflow(self, mock_retrieval_query, mock_connection, mock_storage_query):
        """Test complete memory system workflow"""
        
        # Mock database responses
        mock_storage_query.return_value = []
        mock_retrieval_query.return_value = []
        
        # Mock connection and cursor for storage
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connection.return_value.__enter__.return_value = mock_conn
        
        # Mock psycopg2 connection attributes
        mock_conn.encoding = 'utf-8'
        mock_cursor.connection = mock_conn
        mock_cursor.execute.return_value = None
        mock_cursor.rowcount = 2
        
        # Initialize services
        vectorizer = get_memory_vectorizer()
        storage = get_memory_storage()
        retrieval = get_retrieval_synthesis()
        builder = get_prompt_builder()
        llm = get_llm_service()
        
        # 1. Analyze conversation turn
        user_message = "Gai Media prefers Friday deliveries and I need to check SO-1001 status"
        assistant_message = "I'll check SO-1001 status and note the Friday delivery preference"
        entities = [
            {'name': 'Gai Media', 'type': 'customer', 'confidence': 0.8},
            {'name': 'SO-1001', 'type': 'sales_order', 'confidence': 1.0}
        ]
        
        memories = vectorizer.analyze_conversation_turn(
            user_message, assistant_message, entities, 'test-session', 'test-user'
        )
        
        assert len(memories) > 0
        
        # 2. Store memories
        with patch('psycopg2.extras.execute_values') as mock_execute_values:
            mock_execute_values.return_value = [(1,), (2,)]
            memory_ids = storage.store_memories(memories, 'test-session', 'test-user')
            
            assert len(memory_ids) == 2
        
        # 3. Retrieve and synthesize context
        synthesized_context = retrieval.retrieve_and_synthesize(
            "What are Gai Media's preferences?", 'test-user', entities, 10
        )
        
        assert 'memories' in synthesized_context
        assert 'business_context' in synthesized_context
        assert 'semantic_triples' in synthesized_context
        
        # 4. Build prompt
        prompt = builder.build_prompt("What are Gai Media's preferences?", synthesized_context)
        
        assert "Gai Media" in prompt
        assert "What are Gai Media's preferences?" in prompt
        
        # 5. Generate response
        # Mock the LLM client to use fallback
        llm.client = None
        response = llm.generate_response(prompt, synthesized_context)
        
        assert 'response' in response
        assert 'provider' in response
        assert 'usage' in response
        
        # Check response contains relevant information
        response_text = response['response']
        # The fallback response should be a valid string
        assert len(response_text) > 0
        assert isinstance(response_text, str)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
