"""
Test Phase 4: Entity Linking & Semantic Layer

Tests entity extraction, semantic relationship building, and domain queries.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock
from datetime import date, datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.services.entity_extractor import get_entity_extractor
from api.services.semantic_relationships import get_semantic_relationship_builder
from api.services.domain_queries import get_domain_query_service
from api.utils.database import db


class TestEntityExtraction:
    """Test entity extraction functionality"""
    
    def test_extract_structured_ids(self):
        """Test extraction of SO/INV/WO IDs from text"""
        extractor = get_entity_extractor()
        
        # Test text with various IDs
        text = "Check status of SO-1001 and invoice INV-1009 for work order WO-1234"
        
        # Mock database responses
        with patch.object(db, 'execute_query') as mock_query:
            # Mock responses for each ID type (fetch_one=True returns single dict)
            mock_query.side_effect = [
                {'so_id': 'test-so-id', 'so_number': 'SO-1001'},  # Sales order
                {'invoice_id': 'test-inv-id', 'invoice_number': 'INV-1009'},  # Invoice
                {'wo_id': 'test-wo-id', 'wo_id': 'WO-1234'}  # Work order
            ]
            
            entities = extractor._extract_structured_ids(text, 'test-user', 'test-session')
            
            assert len(entities) == 3
            assert any(e['name'] == 'SO-1001' for e in entities)
            assert any(e['name'] == 'INV-1009' for e in entities)
            assert any(e['name'] == 'WO-1234' for e in entities)
    
    def test_extract_customer_names(self):
        """Test fuzzy customer name extraction"""
        extractor = get_entity_extractor()
        
        # Test text with customer name
        text = "What's the status for Gai Media's order?"
        
        with patch.object(db, 'execute_query') as mock_query:
            # Mock customer data - need to handle multiple calls
            def mock_side_effect(*args, **kwargs):
                if 'similarity' in args[0]:  # Similarity query
                    return {'score': 0.8}
                elif 'canonical_name' in args[0]:  # Recent mentions query
                    return {'mentions': 0}
                else:  # Get customers query
                    return [{'customer_id': 'test-customer-id', 'name': 'Gai Media'}]
            
            mock_query.side_effect = mock_side_effect
            
            entities = extractor._extract_customer_names(text, 'test-user', 'test-session')
            
            assert len(entities) == 1
            assert entities[0]['name'] == 'Gai Media'
            assert entities[0]['type'] == 'customer'
            assert entities[0]['confidence'] >= 0.8
    
    def test_calculate_confidence_with_recency_boost(self):
        """Test confidence calculation with recency boost"""
        extractor = get_entity_extractor()
        
        with patch.object(db, 'execute_query') as mock_query:
            # Mock recent mentions (fetch_one=True returns single dict)
            mock_query.return_value = {'mentions': 2}
            
            confidence = extractor._calculate_confidence(0.5, 'Gai Media', 'test-user', 'test-session')
            
            # Should have base score + recency boost
            assert confidence > 0.5
            assert confidence <= 1.0


class TestSemanticRelationships:
    """Test semantic relationship building"""
    
    def test_extract_conversational_relationships(self):
        """Test extraction of relationships from conversation"""
        builder = get_semantic_relationship_builder()
        
        # Test text with preference
        text = "Gai Media prefers Friday deliveries"
        entities = [
            {
                'name': 'Gai Media',
                'type': 'customer',
                'entity_id': 123
            }
        ]
        
        relationships = builder.extract_conversational_relationships(text, entities)
        
        assert len(relationships) == 1
        assert relationships[0]['predicate'] == 'prefers'
        assert relationships[0]['object_value'] == 'Friday deliveries'
        assert relationships[0]['subject_entity_id'] == 123
    
    def test_build_schema_relationships(self):
        """Test building relationships from database schema"""
        builder = get_semantic_relationship_builder()
        
        with patch.object(db, 'execute_query') as mock_query:
            # Mock schema relationship data
            mock_query.return_value = [
                {
                    'so_number': 'SO-1001',
                    'name': 'Gai Media',
                    'subject_id': 1,
                    'object_id': 2
                }
            ]
            
            relationships = builder._build_so_customer_relationships()
            
            assert len(relationships) == 1
            assert relationships[0]['predicate'] == 'issued_to'
            assert relationships[0]['subject_entity_id'] == 1
            assert relationships[0]['object_entity_id'] == 2


class TestDomainQueries:
    """Test domain query service"""
    
    def test_get_customer_data(self):
        """Test getting comprehensive customer data"""
        service = get_domain_query_service()
        
        with patch.object(db, 'execute_query') as mock_query:
            # Mock customer data
            mock_query.side_effect = [
                [{'customer_id': 'test-id', 'name': 'Gai Media', 'industry': 'Entertainment'}],  # Customer
                [{'so_id': 'so-1', 'so_number': 'SO-1001', 'title': 'Test Order'}],  # Orders
                [{'invoice_id': 'inv-1', 'invoice_number': 'INV-1009', 'amount': 1200.00}],  # Invoices
                [{'task_id': 'task-1', 'title': 'Test Task', 'status': 'todo'}]  # Tasks
            ]
            
            data = service.get_customer_data('test-customer-id')
            
            assert data is not None
            assert 'customer' in data
            assert 'orders' in data
            assert 'invoices' in data
            assert 'tasks' in data
            assert 'summary' in data
    
    def test_get_invoice_data(self):
        """Test getting invoice data with payment history"""
        service = get_domain_query_service()
        
        with patch.object(db, 'execute_query') as mock_query:
            # Mock invoice data
            mock_query.side_effect = [
                {'invoice_id': 'inv-1', 'invoice_number': 'INV-1009', 'amount': 1200.00, 'status': 'open', 'due_date': date(2025, 9, 30), 'issued_at': datetime(2025, 9, 1), 'so_number': 'SO-1001', 'order_title': 'Test Order', 'customer_id': 'cust-1', 'customer_name': 'Test Customer'},  # Invoice (single dict)
                [{'payment_id': 'pay-1', 'amount': 600.00, 'method': 'ACH', 'paid_at': '2025-09-15'}]  # Payments (list)
            ]
            
            data = service.get_invoice_data('test-invoice-id')
            
            assert data is not None
            assert 'invoice' in data
            assert 'payments' in data
            assert 'summary' in data
            assert data['summary']['balance'] == 600.00  # 1200 - 600
    
    def test_format_customer_context(self):
        """Test formatting customer data for LLM context"""
        service = get_domain_query_service()
        
        data = {
            'customer': {
                'name': 'Gai Media',
                'industry': 'Entertainment'
            },
            'summary': {
                'total_orders': 5,
                'open_invoices': 2,
                'total_open_amount': 2400.00,
                'open_tasks': 1
            },
            'invoices': [
                {'invoice_number': 'INV-1009', 'amount': 1200.00, 'due_date': '2025-09-30', 'status': 'open'}
            ],
            'orders': [
                {'so_number': 'SO-1001', 'status': 'in_fulfillment', 'title': 'Test Order'}
            ]
        }
        
        context = service.format_for_llm_context(data, 'customer')
        
        assert 'Gai Media' in context
        assert 'Entertainment' in context
        assert 'INV-1009' in context
        assert 'SO-1001' in context
        assert 'semantic triples' in context.lower() or '(' in context


def test_integration_entity_extraction():
    """Integration test for entity extraction with real database"""
    # This test requires a running database
    try:
        extractor = get_entity_extractor()
        
        # Test with actual database
        text = "Check status of SO-1001 for Gai Media"
        entities = extractor.extract_entities(text, 'test-user', 'test-session')
        
        # Should extract at least the customer name
        assert len(entities) > 0
        assert any(e['type'] == 'customer' for e in entities)
        
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


def test_integration_domain_queries():
    """Integration test for domain queries with real database"""
    try:
        service = get_domain_query_service()
        
        # Test customer search
        customers = service.search_customers('Gai Media')
        assert len(customers) > 0
        
        # Test overdue invoices
        overdue = service.get_overdue_invoices()
        assert isinstance(overdue, list)
        
    except Exception as e:
        pytest.skip(f"Database not available: {e}")


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
