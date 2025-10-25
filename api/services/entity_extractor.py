"""
Entity Extraction Service

Extracts entities from text using regex patterns, fuzzy matching, and semantic similarity.
Links entities to domain database records and creates new entity records as needed.
"""

import re
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from api.utils.database import db
from api.utils.config import settings
from api.services.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extracts and links entities from conversational text to domain database records"""
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        
        # Regex patterns for structured IDs
        self.patterns = {
            'sales_order': r'\b(SO-\d{4})\b',
            'invoice': r'\b(INV-\d{4})\b',
            'work_order': r'\b(WO-\d{4})\b'
        }
        
        # Entity type mappings to domain tables
        self.domain_mappings = {
            'sales_order': ('domain.sales_orders', 'so_number', 'so_id'),
            'invoice': ('domain.invoices', 'invoice_number', 'invoice_id'),
            'work_order': ('domain.work_orders', 'wo_id', 'wo_id')  # Assuming WO has identifier
        }
    
    def extract_entities(self, text: str, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text using multiple strategies:
        1. Deterministic (exact ID/name match)
        2. Fuzzy (trigram similarity)
        3. Semantic (vector similarity)
        
        Returns list of entity dictionaries ready for storage
        """
        entities = []
        
        # 1. Extract structured IDs (deterministic)
        structured_entities = self._extract_structured_ids(text, user_id, session_id)
        entities.extend(structured_entities)
        
        # 2. Extract customer names (fuzzy + semantic)
        customer_entities = self._extract_customer_names(text, user_id, session_id)
        entities.extend(customer_entities)
        
        # 3. Extract other business entities (semantic)
        business_entities = self._extract_business_entities(text, user_id, session_id)
        entities.extend(business_entities)
        
        logger.info(f"Extracted {len(entities)} entities from text: {text[:100]}...")
        return entities
    
    def _extract_structured_ids(self, text: str, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Extract SO/INV/WO IDs using regex patterns"""
        entities = []
        
        for entity_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                entity = self._link_structured_id(match, entity_type, user_id, session_id)
                if entity:
                    entities.append(entity)
        
        return entities
    
    def _link_structured_id(self, identifier: str, entity_type: str, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Link structured ID to domain table record"""
        if entity_type not in self.domain_mappings:
            return None
        
        table, id_column, pk_column = self.domain_mappings[entity_type]
        query = f"SELECT {pk_column}, {id_column} FROM {table} WHERE {id_column} = %s"
        
        result = db.execute_query(query, (identifier,), fetch_one=True)
        if not result:
            logger.warning(f"Structured ID {identifier} not found in {table}")
            return None
        
        # Generate entity embedding for semantic similarity
        entity_text = f"{entity_type} {identifier}"
        entity_embedding = self.embedding_service.embed_text(entity_text) if settings.ENTITY_EMBEDDING_ENABLED else None
        
        return {
            'name': identifier,
            'name_hash': self._hash_name(identifier),
            'canonical_name': identifier,
            'type': entity_type,
            'source': 'db',
            'external_ref': {'table': table, 'id': str(result[pk_column])},
            'confidence': 1.0,
            'entity_embedding': entity_embedding,
            'user_id': user_id,
            'session_id': session_id
        }
    
    def _extract_customer_names(self, text: str, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Extract customer names using fuzzy matching with trigram similarity"""
        entities = []
        
        # Get all customers for fuzzy matching
        customers = db.execute_query("SELECT customer_id, name FROM domain.customers")
        
        for customer in customers:
            name = customer['name']
            
            # Use trigram similarity for fuzzy matching
            similarity_query = "SELECT similarity(%s, %s) AS score"
            result = db.execute_query(similarity_query, (name, text), fetch_one=True)
            score = result['score'] if result else 0.0
            
            # Check if name appears in text or has high similarity
            if name.lower() in text.lower() or score > settings.TRIGRAM_THRESHOLD:
                # Calculate confidence with recency boost
                confidence = self._calculate_confidence(score, name, user_id, session_id)
                
                # Generate entity embedding
                entity_embedding = self.embedding_service.embed_text(name) if settings.ENTITY_EMBEDDING_ENABLED else None
                
                entities.append({
                    'name': name,
                    'name_hash': self._hash_name(name),
                    'canonical_name': name,
                    'type': 'customer',
                    'source': 'db',
                    'external_ref': {'table': 'domain.customers', 'id': str(customer['customer_id'])},
                    'confidence': confidence,
                    'entity_embedding': entity_embedding,
                    'user_id': user_id,
                    'session_id': session_id
                })
        
        return entities
    
    def _extract_business_entities(self, text: str, user_id: str, session_id: str) -> List[Dict[str, Any]]:
        """Extract other business entities using semantic similarity"""
        entities = []
        
        # Extract potential business terms (simplified approach)
        business_keywords = [
            'delivery', 'payment', 'invoice', 'order', 'repair', 'maintenance',
            'shipping', 'billing', 'customer service', 'support'
        ]
        
        for keyword in business_keywords:
            if keyword.lower() in text.lower():
                # Generate entity embedding
                entity_embedding = self.embedding_service.embed_text(keyword) if settings.ENTITY_EMBEDDING_ENABLED else None
                
                entities.append({
                    'name': keyword,
                    'name_hash': self._hash_name(keyword),
                    'canonical_name': keyword,
                    'type': 'business_term',
                    'source': 'message',
                    'external_ref': None,
                    'confidence': 0.7,
                    'entity_embedding': entity_embedding,
                    'user_id': user_id,
                    'session_id': session_id
                })
        
        return entities
    
    def _calculate_confidence(self, base_score: float, entity_name: str, user_id: str, session_id: str) -> float:
        """Calculate confidence with recency boost"""
        # Check recent mentions
        query = """
            SELECT COUNT(*) as mentions
            FROM app.entities
            WHERE user_id = %s
            AND canonical_name = %s
            AND created_at > NOW() - INTERVAL '1 hour'
        """
        result = db.execute_query(query, (user_id, entity_name), fetch_one=True)
        mentions = result['mentions'] if result else 0
        
        # Boost: +0.1 per recent mention, capped at +0.3
        boost = min(mentions * 0.1, 0.3)
        return min(base_score + boost, 1.0)
    
    def _hash_name(self, name: str) -> str:
        """Generate PII-safe hash for entity name"""
        return hashlib.sha256(name.lower().encode()).hexdigest()
    
    def store_entities(self, entities: List[Dict[str, Any]]) -> List[int]:
        """Store extracted entities and return entity IDs"""
        if not entities:
            return []
        
        query = """
            INSERT INTO app.entities 
            (session_id, user_id, name, name_hash, canonical_name, type, source, external_ref, confidence, entity_embedding, created_at)
            VALUES %s
            RETURNING entity_id
        """
        
        values = [
            (
                e['session_id'], e['user_id'], e['name'], e['name_hash'],
                e['canonical_name'], e['type'], e['source'],
                str(e.get('external_ref', {})), e['confidence'],
                e.get('entity_embedding'), 'now()'
            )
            for e in entities
        ]
        
        # Execute with returning
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                from psycopg2.extras import execute_values
                result = execute_values(cur, query, values, fetch=True)
                return [row[0] for row in result]
    
    def find_entity_by_name(self, name: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Find existing entity by name hash"""
        name_hash = self._hash_name(name)
        query = """
            SELECT entity_id, name, canonical_name, type, source, external_ref, confidence
            FROM app.entities
            WHERE name_hash = %s AND user_id = %s
            ORDER BY confidence DESC, created_at DESC
            LIMIT 1
        """
        return db.execute_query(query, (name_hash, user_id), fetch_one=True)
    
    def get_entity_aliases(self, entity_id: int) -> List[Dict[str, Any]]:
        """Get all aliases for an entity"""
        query = """
            SELECT alias_text, source, confidence
            FROM app.entity_aliases
            WHERE canonical_entity_id = %s
            ORDER BY confidence DESC
        """
        return db.execute_query(query, (entity_id,))
    
    def create_entity_alias(self, canonical_entity_id: int, alias_text: str, source: str, confidence: float = 1.0):
        """Create an alias for an entity"""
        alias_hash = self._hash_name(alias_text)
        query = """
            INSERT INTO app.entity_aliases (canonical_entity_id, alias_text, alias_hash, source, confidence, created_at)
            VALUES (%s, %s, %s, %s, %s, now())
            ON CONFLICT (alias_hash, canonical_entity_id) DO NOTHING
        """
        db.execute_query(query, (canonical_entity_id, alias_text, alias_hash, source, confidence))


# Singleton instance
_entity_extractor = None

def get_entity_extractor() -> EntityExtractor:
    """Get singleton instance of EntityExtractor"""
    global _entity_extractor
    if _entity_extractor is None:
        _entity_extractor = EntityExtractor()
    return _entity_extractor
