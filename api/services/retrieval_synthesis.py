"""
Retrieval & Synthesis Service

Implements hybrid search combining vector similarity, full-text search, and trigram matching.
Synthesizes memories with business context for LLM consumption.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone

from api.utils.database import db
from api.utils.config import settings
from api.services.embeddings import get_embedding_service
from api.services.memory_storage import get_memory_storage
from api.services.domain_queries import get_domain_query_service
from api.services.semantic_relationships import get_semantic_relationship_builder
from api.services.entity_extractor import get_entity_extractor

logger = logging.getLogger(__name__)


class RetrievalSynthesis:
    """Hybrid search and synthesis of memories with business context"""
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.memory_storage = get_memory_storage()
        self.domain_queries = get_domain_query_service()
        self.semantic_relationships = get_semantic_relationship_builder()
        self.entity_extractor = get_entity_extractor()
        
        # Search weights for hybrid scoring
        self.search_weights = {
            'vector': 0.4,
            'fulltext': 0.3,
            'trigram': 0.2,
            'recency': 0.1
        }
        
        # Memory type importance weights
        self.memory_type_weights = {
            'commitment': 1.0,
            'policy': 0.9,
            'semantic': 0.8,
            'todo': 0.7,
            'profile': 0.6,
            'episodic': 0.5
        }
    
    def retrieve_and_synthesize(
        self, 
        query: str, 
        user_id: str, 
        entities: List[Dict[str, Any]],
        max_memories: int = 10,
        include_business_context: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve and synthesize memories with business context
        
        Args:
            query: User query
            user_id: User identifier
            entities: Extracted entities from query
            max_memories: Maximum number of memories to retrieve
            include_business_context: Whether to include business context
            
        Returns:
            Dictionary containing synthesized context for LLM
        """
        # 1. Retrieve memories using hybrid search
        memories = self._hybrid_search(query, user_id, entities, max_memories)
        
        # 2. Get business context for entities
        business_context = {}
        if include_business_context and entities:
            business_context = self._get_business_context(entities)
        
        # 3. Get semantic relationships
        relationships = []
        if entities:
            relationships = self._get_entity_relationships(entities)
        
        # 4. Synthesize context
        synthesized_context = self._synthesize_context(
            memories, business_context, relationships, query
        )
        
        return synthesized_context
    
    def _hybrid_search(
        self, 
        query: str, 
        user_id: str, 
        entities: List[Dict[str, Any]], 
        max_memories: int
    ) -> List[Dict[str, Any]]:
        """Perform hybrid search combining multiple search methods"""
        
        # 1. Vector similarity search
        vector_results = self._vector_search(query, user_id, max_memories)
        
        # 2. Full-text search
        fulltext_results = self._fulltext_search(query, user_id, max_memories)
        
        # 3. Trigram similarity search
        trigram_results = self._trigram_search(query, user_id, max_memories)
        
        # 4. Entity-based search
        entity_results = []
        if entities:
            entity_names = [e['name'] for e in entities]
            entity_results = self.memory_storage.get_memories_by_entities(
                user_id, entity_names, max_memories
            )
        
        # 5. Combine and score results
        combined_results = self._combine_search_results(
            vector_results, fulltext_results, trigram_results, entity_results, query
        )
        
        # 6. Apply recency boost and return top results
        final_results = self._apply_recency_boost(combined_results)
        return final_results[:max_memories]
    
    def _vector_search(self, query: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Vector similarity search using embeddings"""
        if not settings.ENABLE_VECTORS:
            return []
        
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)
        if not query_embedding:
            return []
        
        # Search for similar memories
        query_sql = """
            SELECT 
                memory_id, 
                kind, 
                text, 
                importance, 
                created_at, 
                expires_at,
                provenance,
                1 - (embedding <=> %s::vector) as similarity
            FROM app.memories
            WHERE user_id = %s
            AND (expires_at IS NULL OR expires_at > NOW())
            AND embedding IS NOT NULL
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        
        results = db.execute_query(query_sql, (query_embedding, user_id, query_embedding, limit))
        
        # Add search method metadata
        for result in results:
            result['search_method'] = 'vector'
            result['search_score'] = result['similarity']
        
        return results
    
    def _fulltext_search(self, query: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Full-text search using PostgreSQL FTS"""
        query_sql = """
            SELECT 
                memory_id, 
                kind, 
                text, 
                importance, 
                created_at, 
                expires_at,
                provenance,
                ts_rank(to_tsvector('english', text), plainto_tsquery('english', %s)) as rank
            FROM app.memories
            WHERE user_id = %s
            AND (expires_at IS NULL OR expires_at > NOW())
            AND to_tsvector('english', text) @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC
            LIMIT %s
        """
        
        results = db.execute_query(query_sql, (query, user_id, query, limit))
        
        # Add search method metadata
        for result in results:
            result['search_method'] = 'fulltext'
            result['search_score'] = result['rank']
        
        return results
    
    def _trigram_search(self, query: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
        """Trigram similarity search"""
        query_sql = """
            SELECT 
                memory_id, 
                kind, 
                text, 
                importance, 
                created_at, 
                expires_at,
                provenance,
                similarity(text, %s) as trigram_score
            FROM app.memories
            WHERE user_id = %s
            AND (expires_at IS NULL OR expires_at > NOW())
            AND similarity(text, %s) > 0.1
            ORDER BY similarity(text, %s) DESC
            LIMIT %s
        """
        
        results = db.execute_query(query_sql, (query, user_id, query, query, limit))
        
        # Add search method metadata
        for result in results:
            result['search_method'] = 'trigram'
            result['search_score'] = result['trigram_score']
        
        return results
    
    def _combine_search_results(
        self, 
        vector_results: List[Dict[str, Any]], 
        fulltext_results: List[Dict[str, Any]], 
        trigram_results: List[Dict[str, Any]], 
        entity_results: List[Dict[str, Any]], 
        query: str
    ) -> List[Dict[str, Any]]:
        """Combine results from different search methods with hybrid scoring"""
        
        # Create memory ID to result mapping
        memory_map = {}
        
        # Add results from each method
        for results, method in [
            (vector_results, 'vector'),
            (fulltext_results, 'fulltext'),
            (trigram_results, 'trigram'),
            (entity_results, 'entity')
        ]:
            for result in results:
                memory_id = result['memory_id']
                
                if memory_id not in memory_map:
                    memory_map[memory_id] = result.copy()
                    memory_map[memory_id]['search_methods'] = []
                    memory_map[memory_id]['hybrid_score'] = 0.0
                
                # Track which methods found this memory
                memory_map[memory_id]['search_methods'].append(method)
                
                # Add method-specific score
                method_score = result.get('search_score', 0.0)
                weight = self.search_weights.get(method, 0.1)
                memory_map[memory_id]['hybrid_score'] += method_score * weight
        
        # Convert back to list and sort by hybrid score
        combined_results = list(memory_map.values())
        combined_results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        return combined_results
    
    def _apply_recency_boost(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply recency boost to search results"""
        if not results:
            return results
        
        # Calculate recency boost
        now = datetime.now(timezone.utc)
        for result in results:
            created_at = result['created_at']
            if isinstance(created_at, str):
                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
            # Calculate days since creation
            days_old = (now - created_at).days
            
            # Apply recency boost (newer memories get higher scores)
            recency_boost = max(0, 1.0 - (days_old / 30.0))  # Boost decays over 30 days
            result['hybrid_score'] += recency_boost * self.search_weights['recency']
        
        # Re-sort by updated hybrid score
        results.sort(key=lambda x: x['hybrid_score'], reverse=True)
        return results
    
    def _get_business_context(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get business context for entities"""
        business_context = {}
        
        for entity in entities:
            entity_type = entity.get('type')
            entity_name = entity.get('name')
            
            if entity_type == 'customer' and entity_name:
                # Get customer data using external_ref ID
                external_ref = entity.get('external_ref', {})
                customer_id = external_ref.get('id')
                if customer_id:
                    customer_data = self.domain_queries.get_customer_data(customer_id)
                    if customer_data:
                        business_context[entity_name] = customer_data
            
            elif entity_type == 'sales_order' and entity_name:
                # Get order data
                order_data = self.domain_queries.get_sales_order_data(entity_name)
                if order_data:
                    business_context[entity_name] = order_data
            
            elif entity_type == 'invoice' and entity_name:
                # Get invoice data
                invoice_data = self.domain_queries.get_invoice_data(entity_name)
                if invoice_data:
                    business_context[entity_name] = invoice_data
        
        return business_context
    
    def _get_entity_relationships(self, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Get semantic relationships for entities
        
        This looks up relationships stored in app.entity_relationships table
        for the entities found in the conversation.
        """
        relationships = []
        entity_ids = []
        
        # First, find entity IDs for each entity name
        for entity in entities:
            entity_name = entity.get('name')
            user_id = entity.get('user_id')
            
            if entity_name and user_id:
                # Find the entity in the database by name
                entity_record = self.entity_extractor.find_entity_by_name(entity_name, user_id)
                if entity_record and entity_record.get('entity_id'):
                    entity_ids.append(entity_record['entity_id'])
        
        # Get relationships for found entity IDs
        if entity_ids:
            relationships = self.semantic_relationships.get_relationships_for_entities(entity_ids)
        
        return relationships
    
    def _synthesize_context(
        self, 
        memories: List[Dict[str, Any]], 
        business_context: Dict[str, Any], 
        relationships: List[Dict[str, Any]], 
        query: str
    ) -> Dict[str, Any]:
        """Synthesize all context into structured format for LLM"""
        
        # Group memories by type
        memories_by_type = {}
        for memory in memories:
            memory_type = memory['kind']
            if memory_type not in memories_by_type:
                memories_by_type[memory_type] = []
            memories_by_type[memory_type].append(memory)
        
        # Create semantic triples from memories
        memory_triples = []
        for memory in memories:
            # Extract key information from memory text
            memory_text = memory['text']
            memory_type = memory['kind']
            
            # Create semantic triple representation
            if memory_type == 'semantic':
                # Parse semantic memory into triple
                if ':' in memory_text:
                    parts = memory_text.split(':', 1)
                    if len(parts) == 2:
                        subject = parts[0].strip()
                        predicate_object = parts[1].strip()
                        memory_triples.append({
                            'subject': subject,
                            'predicate': 'has_property',
                            'object': predicate_object,
                            'source': 'memory',
                            'confidence': memory['importance']
                        })
            
            elif memory_type == 'commitment':
                memory_triples.append({
                    'subject': 'user',
                    'predicate': 'committed_to',
                    'object': memory_text,
                    'source': 'memory',
                    'confidence': memory['importance']
                })
            
            elif memory_type == 'semantic' and 'prefer' in memory_text.lower():
                memory_triples.append({
                    'subject': 'user',
                    'predicate': 'prefers',
                    'object': memory_text,
                    'source': 'memory',
                    'confidence': memory['importance']
                })
        
        # Create business context triples
        business_triples = []
        for entity_name, context in business_context.items():
            if isinstance(context, dict):
                # Add customer information
                if 'customer' in context:
                    customer = context['customer']
                    business_triples.append({
                        'subject': entity_name,
                        'predicate': 'is_customer',
                        'object': f"Industry: {customer.get('industry', 'Unknown')}",
                        'source': 'business_data',
                        'confidence': 1.0
                    })
                
                # Add order information
                if 'orders' in context:
                    for order in context['orders']:
                        business_triples.append({
                            'subject': entity_name,
                            'predicate': 'has_order',
                            'object': f"{order.get('so_number', 'Unknown')} - {order.get('status', 'Unknown')}",
                            'source': 'business_data',
                            'confidence': 1.0
                        })
                
                # Add invoice information
                if 'invoices' in context:
                    for invoice in context['invoices']:
                        business_triples.append({
                            'subject': entity_name,
                            'predicate': 'has_invoice',
                            'object': f"{invoice.get('invoice_number', 'Unknown')} - ${invoice.get('amount', 0)}",
                            'source': 'business_data',
                            'confidence': 1.0
                        })
        
        # Combine all triples
        all_triples = memory_triples + business_triples + relationships
        
        # Create summary
        summary = self._create_context_summary(memories, business_context, relationships, query)
        
        return {
            'query': query,
            'memories': memories,
            'business_context': business_context,
            'relationships': relationships,
            'semantic_triples': all_triples,
            'summary': summary,
            'metadata': {
                'total_memories': len(memories),
                'memory_types': list(memories_by_type.keys()),
                'business_entities': list(business_context.keys()),
                'total_triples': len(all_triples),
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
        }
    
    def _create_context_summary(
        self, 
        memories: List[Dict[str, Any]], 
        business_context: Dict[str, Any], 
        relationships: List[Dict[str, Any]], 
        query: str
    ) -> str:
        """Create a human-readable summary of the context"""
        
        summary_parts = []
        
        # Add memory summary
        if memories:
            memory_types = {}
            for memory in memories:
                memory_type = memory['kind']
                memory_types[memory_type] = memory_types.get(memory_type, 0) + 1
            
            memory_summary = f"Found {len(memories)} relevant memories: "
            memory_summary += ", ".join([f"{count} {kind}" for kind, count in memory_types.items()])
            summary_parts.append(memory_summary)
        
        # Add business context summary
        if business_context:
            context_summary = f"Business context available for {len(business_context)} entities: "
            context_summary += ", ".join(business_context.keys())
            summary_parts.append(context_summary)
        
        # Add relationships summary
        if relationships:
            summary_parts.append(f"Found {len(relationships)} semantic relationships")
        
        # Add query context
        summary_parts.append(f"Query: {query}")
        
        return ". ".join(summary_parts) + "."


# Singleton instance
_retrieval_synthesis = None

def get_retrieval_synthesis() -> RetrievalSynthesis:
    """Get singleton instance of RetrievalSynthesis"""
    global _retrieval_synthesis
    if _retrieval_synthesis is None:
        _retrieval_synthesis = RetrievalSynthesis()
    return _retrieval_synthesis
