"""
Semantic Relationship Builder

Extracts and stores semantic triples (subject-predicate-object) from:
1. Database schema (foreign key relationships)
2. Conversational text (user preferences, policies)
3. Inferred relationships

Stores relationships in app.entity_relationships table with embeddings.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import re

from api.utils.database import db
from api.utils.config import settings
from api.services.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class SemanticRelationshipBuilder:
    """Builds semantic triples from database schema and conversations"""
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        
        # Relationship patterns for conversational extraction
        self.relationship_patterns = {
            'prefers': [
                r'prefer(?:s)?\s+(.+)',
                r'likes?\s+(.+)',
                r'wants?\s+(.+)'
            ],
            'requires': [
                r'require(?:s)?\s+(.+)',
                r'needs?\s+(.+)',
                r'must\s+(.+)'
            ],
            'has_policy': [
                r'policy\s+(.+)',
                r'rule\s+(.+)',
                r'always\s+(.+)',
                r'never\s+(.+)'
            ],
            'has_commitment': [
                r'promise(?:s)?\s+(.+)',
                r'commit(?:s)?\s+(.+)',
                r'agree(?:s)?\s+(.+)'
            ]
        }
    
    def build_schema_relationships(self) -> List[Dict[str, Any]]:
        """
        Extract semantic relationships from foreign key constraints
        Example: sales_order -> customer becomes (SO-1001, issued_to, Gai Media)
        """
        if not settings.ENABLE_SEMANTIC_RELATIONSHIPS:
            return []
        
        relationships = []
        
        # Sales Order -> Customer
        so_customer_rels = self._build_so_customer_relationships()
        relationships.extend(so_customer_rels)
        
        # Invoice -> Sales Order
        inv_so_rels = self._build_invoice_so_relationships()
        relationships.extend(inv_so_rels)
        
        # Work Order -> Sales Order
        wo_so_rels = self._build_wo_so_relationships()
        relationships.extend(wo_so_rels)
        
        # Payment -> Invoice
        pay_inv_rels = self._build_payment_invoice_relationships()
        relationships.extend(pay_inv_rels)
        
        logger.info(f"Built {len(relationships)} schema relationships")
        return relationships
    
    def _build_so_customer_relationships(self) -> List[Dict[str, Any]]:
        """Build sales order to customer relationships"""
        query = """
            SELECT 
                so.so_number,
                c.name,
                e_so.entity_id as subject_id,
                e_cust.entity_id as object_id
            FROM domain.sales_orders so
            JOIN domain.customers c ON so.customer_id = c.customer_id
            LEFT JOIN app.entities e_so ON e_so.external_ref->>'id' = so.so_id::text
            LEFT JOIN app.entities e_cust ON e_cust.external_ref->>'id' = c.customer_id::text
            WHERE e_so.entity_id IS NOT NULL AND e_cust.entity_id IS NOT NULL
        """
        
        results = db.execute_query(query)
        relationships = []
        
        for row in results:
            triple_text = f"{row['so_number']} issued_to {row['name']}"
            embedding = self.embedding_service.embed_text(triple_text) if settings.ENTITY_EMBEDDING_ENABLED else None
            
            relationships.append({
                'subject_entity_id': row['subject_id'],
                'predicate': 'issued_to',
                'object_entity_id': row['object_id'],
                'object_value': None,
                'relationship_embedding': embedding,
                'confidence': 1.0,
                'source': 'db_schema'
            })
        
        return relationships
    
    def _build_invoice_so_relationships(self) -> List[Dict[str, Any]]:
        """Build invoice to sales order relationships"""
        query = """
            SELECT 
                i.invoice_number,
                so.so_number,
                e_inv.entity_id as subject_id,
                e_so.entity_id as object_id
            FROM domain.invoices i
            JOIN domain.sales_orders so ON i.so_id = so.so_id
            LEFT JOIN app.entities e_inv ON e_inv.external_ref->>'id' = i.invoice_id::text
            LEFT JOIN app.entities e_so ON e_so.external_ref->>'id' = so.so_id::text
            WHERE e_inv.entity_id IS NOT NULL AND e_so.entity_id IS NOT NULL
        """
        
        results = db.execute_query(query)
        relationships = []
        
        for row in results:
            triple_text = f"{row['invoice_number']} belongs_to {row['so_number']}"
            embedding = self.embedding_service.embed_text(triple_text) if settings.ENTITY_EMBEDDING_ENABLED else None
            
            relationships.append({
                'subject_entity_id': row['subject_id'],
                'predicate': 'belongs_to',
                'object_entity_id': row['object_id'],
                'object_value': None,
                'relationship_embedding': embedding,
                'confidence': 1.0,
                'source': 'db_schema'
            })
        
        return relationships
    
    def _build_wo_so_relationships(self) -> List[Dict[str, Any]]:
        """Build work order to sales order relationships"""
        query = """
            SELECT 
                wo.wo_id,
                so.so_number,
                e_wo.entity_id as subject_id,
                e_so.entity_id as object_id
            FROM domain.work_orders wo
            JOIN domain.sales_orders so ON wo.so_id = so.so_id
            LEFT JOIN app.entities e_wo ON e_wo.external_ref->>'id' = wo.wo_id::text
            LEFT JOIN app.entities e_so ON e_so.external_ref->>'id' = so.so_id::text
            WHERE e_wo.entity_id IS NOT NULL AND e_so.entity_id IS NOT NULL
        """
        
        results = db.execute_query(query)
        relationships = []
        
        for row in results:
            triple_text = f"WO-{row['wo_id'][:8]}... belongs_to {row['so_number']}"
            embedding = self.embedding_service.embed_text(triple_text) if settings.ENTITY_EMBEDDING_ENABLED else None
            
            relationships.append({
                'subject_entity_id': row['subject_id'],
                'predicate': 'belongs_to',
                'object_entity_id': row['object_id'],
                'object_value': None,
                'relationship_embedding': embedding,
                'confidence': 1.0,
                'source': 'db_schema'
            })
        
        return relationships
    
    def _build_payment_invoice_relationships(self) -> List[Dict[str, Any]]:
        """Build payment to invoice relationships"""
        query = """
            SELECT 
                p.payment_id,
                i.invoice_number,
                e_pay.entity_id as subject_id,
                e_inv.entity_id as object_id
            FROM domain.payments p
            JOIN domain.invoices i ON p.invoice_id = i.invoice_id
            LEFT JOIN app.entities e_pay ON e_pay.external_ref->>'id' = p.payment_id::text
            LEFT JOIN app.entities e_inv ON e_inv.external_ref->>'id' = i.invoice_id::text
            WHERE e_pay.entity_id IS NOT NULL AND e_inv.entity_id IS NOT NULL
        """
        
        results = db.execute_query(query)
        relationships = []
        
        for row in results:
            triple_text = f"Payment-{row['payment_id'][:8]}... pays {row['invoice_number']}"
            embedding = self.embedding_service.embed_text(triple_text) if settings.ENTITY_EMBEDDING_ENABLED else None
            
            relationships.append({
                'subject_entity_id': row['subject_id'],
                'predicate': 'pays',
                'object_entity_id': row['object_id'],
                'object_value': None,
                'relationship_embedding': embedding,
                'confidence': 1.0,
                'source': 'db_schema'
            })
        
        return relationships
    
    def extract_conversational_relationships(self, text: str, entities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract relationships from conversation
        Example: "Gai Media prefers Friday deliveries" -> (Gai Media, prefers, Friday deliveries)
        """
        if not settings.ENABLE_SEMANTIC_RELATIONSHIPS:
            return []
        
        relationships = []
        
        # Find customer entities
        customer_entities = [e for e in entities if e.get('type') == 'customer']
        
        for predicate, patterns in self.relationship_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    # Extract the object value
                    object_value = match.group(1).strip()
                    
                    # Find the most relevant customer entity
                    customer_entity = self._find_most_relevant_customer(customer_entities, text, match.start())
                    
                    if customer_entity and customer_entity.get('entity_id'):
                        triple_text = f"{customer_entity['name']} {predicate} {object_value}"
                        embedding = self.embedding_service.embed_text(triple_text) if settings.ENTITY_EMBEDDING_ENABLED else None
                        
                        relationships.append({
                            'subject_entity_id': customer_entity['entity_id'],
                            'predicate': predicate,
                            'object_entity_id': None,
                            'object_value': object_value,
                            'relationship_embedding': embedding,
                            'confidence': 0.8,
                            'source': 'conversation'
                        })
        
        logger.info(f"Extracted {len(relationships)} conversational relationships")
        return relationships
    
    def _find_most_relevant_customer(self, customer_entities: List[Dict[str, Any]], text: str, match_position: int) -> Optional[Dict[str, Any]]:
        """Find the customer entity most relevant to the relationship"""
        if not customer_entities:
            return None
        
        # If only one customer, return it
        if len(customer_entities) == 1:
            return customer_entities[0]
        
        # Find customer mentioned closest to the relationship
        best_entity = None
        min_distance = float('inf')
        
        for entity in customer_entities:
            name = entity['name']
            # Find all occurrences of the customer name
            for match in re.finditer(re.escape(name), text, re.IGNORECASE):
                distance = abs(match.start() - match_position)
                if distance < min_distance:
                    min_distance = distance
                    best_entity = entity
        
        return best_entity or customer_entities[0]
    
    def store_relationships(self, relationships: List[Dict[str, Any]]) -> List[int]:
        """Store relationships in database and return relationship IDs"""
        if not relationships:
            return []
        
        query = """
            INSERT INTO app.entity_relationships 
            (subject_entity_id, predicate, object_entity_id, object_value, relationship_embedding, confidence, source, created_at)
            VALUES %s
            RETURNING relationship_id
        """
        
        values = [
            (
                r['subject_entity_id'], r['predicate'], r['object_entity_id'],
                r['object_value'], r.get('relationship_embedding'), r['confidence'], r['source'], 'now()'
            )
            for r in relationships if r.get('subject_entity_id')
        ]
        
        if not values:
            return []
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                from psycopg2.extras import execute_values
                result = execute_values(cur, query, values, fetch=True)
                return [row[0] for row in result]
    
    def get_relationships_for_entities(self, entity_ids: List[int]) -> List[Dict[str, Any]]:
        """Get all relationships for given entity IDs"""
        if not entity_ids:
            return []
        
        query = """
            SELECT 
                r.relationship_id,
                r.predicate,
                r.object_value,
                r.confidence,
                r.source,
                e1.name as subject_name,
                e2.name as object_name
            FROM app.entity_relationships r
            LEFT JOIN app.entities e1 ON r.subject_entity_id = e1.entity_id
            LEFT JOIN app.entities e2 ON r.object_entity_id = e2.entity_id
            WHERE r.subject_entity_id = ANY(%s)
            ORDER BY r.confidence DESC, r.created_at DESC
        """
        
        return db.execute_query(query, (entity_ids,))
    
    def search_relationships(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search relationships using semantic similarity"""
        if not settings.ENTITY_EMBEDDING_ENABLED:
            return []
        
        query_embedding = self.embedding_service.embed_text(query_text)
        
        query = """
            SELECT 
                r.relationship_id,
                r.predicate,
                r.object_value,
                r.confidence,
                r.source,
                e1.name as subject_name,
                e2.name as object_name,
                1 - (r.relationship_embedding <=> %s::vector) as similarity
            FROM app.entity_relationships r
            LEFT JOIN app.entities e1 ON r.subject_entity_id = e1.entity_id
            LEFT JOIN app.entities e2 ON r.object_entity_id = e2.entity_id
            WHERE r.relationship_embedding IS NOT NULL
            ORDER BY r.relationship_embedding <=> %s::vector
            LIMIT %s
        """
        
        return db.execute_query(query, (query_embedding, query_embedding, limit))


# Singleton instance
_semantic_relationship_builder = None

def get_semantic_relationship_builder() -> SemanticRelationshipBuilder:
    """Get singleton instance of SemanticRelationshipBuilder"""
    global _semantic_relationship_builder
    if _semantic_relationship_builder is None:
        _semantic_relationship_builder = SemanticRelationshipBuilder()
    return _semantic_relationship_builder
