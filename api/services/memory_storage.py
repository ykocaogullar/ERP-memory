"""
Memory Storage Service

Stores memories with PII redaction, deduplication, and TTL management.
Handles batch operations and memory lifecycle management.
"""

import logging
import re
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from api.utils.database import db
from api.utils.config import settings

logger = logging.getLogger(__name__)


class MemoryStorage:
    """Stores memories with PII redaction, deduplication, and TTL management"""
    
    def __init__(self):
        # PII patterns for redaction
        self.pii_patterns = {
            'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
            'ip_address': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            'url': r'https?://[^\s]+',
            'date_of_birth': r'\b\d{1,2}/\d{1,2}/\d{4}\b'
        }
        
        # PII replacement tokens
        self.pii_tokens = {
            'email': '[EMAIL]',
            'phone': '[PHONE]',
            'ssn': '[SSN]',
            'credit_card': '[CARD]',
            'ip_address': '[IP]',
            'url': '[URL]',
            'date_of_birth': '[DOB]'
        }
    
    def store_memories(
        self, 
        memories: List[Dict[str, Any]], 
        session_id: str, 
        user_id: str
    ) -> List[int]:
        """
        Store memories with PII redaction and deduplication
        
        Args:
            memories: List of memory dictionaries
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            List of memory IDs that were stored
        """
        if not memories:
            return []
        
        # Apply PII redaction
        redacted_memories = []
        for memory in memories:
            redacted_memory = self._redact_pii(memory.copy())
            redacted_memories.append(redacted_memory)
        
        # Calculate expiry dates
        for memory in redacted_memories:
            if memory.get('ttl_days'):
                memory['expires_at'] = datetime.now() + timedelta(days=memory['ttl_days'])
            else:
                memory['expires_at'] = None
        
        # Check for duplicates
        unique_memories = self._deduplicate(redacted_memories, user_id)
        
        if not unique_memories:
            logger.info("All memories were duplicates, nothing to store")
            return []
        
        # Store in database
        memory_ids = self._store_in_database(unique_memories, session_id, user_id)
        
        logger.info(f"Stored {len(memory_ids)} unique memories for user {user_id}")
        return memory_ids
    
    def _redact_pii(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Redact PII from memory text"""
        if not settings.ENABLE_PII_REDACTION:
            return memory
        
        text = memory['text']
        redacted_text = text
        pii_found = {}
        
        for pii_type, pattern in self.pii_patterns.items():
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Generate a hash for tracking
                match_hash = hashlib.sha256(match.encode()).hexdigest()[:8]
                token = f"{self.pii_tokens[pii_type]}_{match_hash}"
                
                # Replace in text
                redacted_text = redacted_text.replace(match, token)
                
                # Track what was redacted
                if pii_type not in pii_found:
                    pii_found[pii_type] = []
                pii_found[pii_type].append({
                    'original': match,
                    'token': token,
                    'hash': match_hash
                })
        
        memory['text'] = redacted_text
        
        # Add PII tracking to provenance
        if pii_found:
            if 'provenance' not in memory:
                memory['provenance'] = {}
            memory['provenance']['pii_redacted'] = pii_found
        
        return memory
    
    def _deduplicate(
        self, 
        memories: List[Dict[str, Any]], 
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Remove duplicate memories based on content hash"""
        if not memories:
            return []
        
        # Get recent memory hashes for this user
        recent_hashes = self._get_recent_memory_hashes(user_id)
        
        unique_memories = []
        for memory in memories:
            # Create content hash
            content_hash = self._create_content_hash(memory['text'])
            
            # Check if this memory already exists
            if content_hash not in recent_hashes:
                unique_memories.append(memory)
                recent_hashes.add(content_hash)
            else:
                logger.debug(f"Skipping duplicate memory: {memory['text'][:50]}...")
        
        return unique_memories
    
    def _get_recent_memory_hashes(self, user_id: str) -> set:
        """Get hashes of recent memories for deduplication"""
        query = """
            SELECT content_hash
            FROM app.memories
            WHERE user_id = %s
            AND created_at > NOW() - INTERVAL '24 hours'
        """
        
        results = db.execute_query(query, (user_id,))
        return {row['content_hash'] for row in results if row.get('content_hash')}
    
    def _create_content_hash(self, text: str) -> str:
        """Create a hash for memory content"""
        # Normalize text for hashing
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _store_in_database(
        self, 
        memories: List[Dict[str, Any]], 
        session_id: str, 
        user_id: str
    ) -> List[int]:
        """Store memories in database and return memory IDs"""
        if not memories:
            return []
        
        query = """
            INSERT INTO app.memories 
            (session_id, user_id, kind, text, embedding, importance, ttl_days, expires_at, provenance, created_at)
            VALUES %s
            RETURNING memory_id
        """
        
        values = []
        for memory in memories:
            # Create content hash
            content_hash = self._create_content_hash(memory['text'])
            
            values.append((
                session_id,
                user_id,
                memory['kind'],
                memory['text'],
                memory.get('embedding'),
                memory['importance'],
                memory.get('ttl_days'),
                memory.get('expires_at'),
                str(memory.get('provenance', {})),
                datetime.now()
            ))
        
        # Store in database
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                from psycopg2.extras import execute_values
                result = execute_values(cur, query, values, fetch=True)
                memory_ids = [row[0] for row in result]
                
                # Update content_hash for stored memories
                self._update_content_hashes(memory_ids, memories)
                
                return memory_ids
    
    def _update_content_hashes(self, memory_ids: List[int], memories: List[Dict[str, Any]]):
        """Update content_hash for stored memories"""
        if not memory_ids or not memories:
            return
        
        # Create mapping of memory_id to content_hash
        id_to_hash = {}
        for i, memory_id in enumerate(memory_ids):
            if i < len(memories):
                content_hash = self._create_content_hash(memories[i]['text'])
                id_to_hash[memory_id] = content_hash
        
        # Update content_hash in database
        for memory_id, content_hash in id_to_hash.items():
            update_query = """
                UPDATE app.memories 
                SET content_hash = %s 
                WHERE memory_id = %s
            """
            db.execute_query(update_query, (content_hash, memory_id))
    
    def get_memories(
        self, 
        user_id: str, 
        limit: int = 10, 
        kind: Optional[str] = None,
        include_expired: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories for a user
        
        Args:
            user_id: User identifier
            limit: Maximum number of memories to return
            kind: Optional memory kind filter
            include_expired: Whether to include expired memories
            
        Returns:
            List of memory dictionaries
        """
        query = """
            SELECT memory_id, kind, text, importance, created_at, expires_at, provenance
            FROM app.memories
            WHERE user_id = %s
        """
        params = [user_id]
        
        if not include_expired:
            query += " AND (expires_at IS NULL OR expires_at > NOW())"
        
        if kind:
            query += " AND kind = %s"
            params.append(kind)
        
        query += " ORDER BY importance DESC, created_at DESC LIMIT %s"
        params.append(limit)
        
        return db.execute_query(query, tuple(params))
    
    def get_memories_by_entities(
        self, 
        user_id: str, 
        entity_names: List[str], 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories that mention specific entities
        
        Args:
            user_id: User identifier
            entity_names: List of entity names to search for
            limit: Maximum number of memories to return
            
        Returns:
            List of memory dictionaries
        """
        if not entity_names:
            return []
        
        # Create search pattern for entity names
        search_patterns = []
        for entity_name in entity_names:
            # Escape special regex characters
            escaped_name = re.escape(entity_name)
            search_patterns.append(f"\\b{escaped_name}\\b")
        
        # Combine patterns with OR
        combined_pattern = "|".join(search_patterns)
        
        query = """
            SELECT memory_id, kind, text, importance, created_at, expires_at, provenance
            FROM app.memories
            WHERE user_id = %s
            AND (expires_at IS NULL OR expires_at > NOW())
            AND text ~* %s
            ORDER BY importance DESC, created_at DESC
            LIMIT %s
        """
        
        return db.execute_query(query, (user_id, combined_pattern, limit))
    
    def update_memory_importance(self, memory_id: int, new_importance: float):
        """Update the importance score of a memory"""
        query = """
            UPDATE app.memories 
            SET importance = %s, updated_at = NOW()
            WHERE memory_id = %s
        """
        db.execute_query(query, (new_importance, memory_id))
    
    def delete_expired_memories(self, user_id: Optional[str] = None) -> int:
        """
        Delete expired memories
        
        Args:
            user_id: Optional user ID to limit deletion to specific user
            
        Returns:
            Number of memories deleted
        """
        if user_id:
            query = """
                DELETE FROM app.memories 
                WHERE user_id = %s AND expires_at IS NOT NULL AND expires_at <= NOW()
            """
            params = (user_id,)
        else:
            query = """
                DELETE FROM app.memories 
                WHERE expires_at IS NOT NULL AND expires_at <= NOW()
            """
            params = ()
        
        with db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                deleted_count = cur.rowcount
        
        logger.info(f"Deleted {deleted_count} expired memories")
        return deleted_count
    
    def get_memory_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for a user"""
        query = """
            SELECT 
                kind,
                COUNT(*) as count,
                AVG(importance) as avg_importance,
                COUNT(CASE WHEN expires_at IS NULL OR expires_at > NOW() THEN 1 END) as active_count,
                COUNT(CASE WHEN expires_at IS NOT NULL AND expires_at <= NOW() THEN 1 END) as expired_count
            FROM app.memories
            WHERE user_id = %s
            GROUP BY kind
        """
        
        results = db.execute_query(query, (user_id,))
        
        stats = {
            'by_kind': {row['kind']: dict(row) for row in results},
            'total_memories': sum(row['count'] for row in results),
            'active_memories': sum(row['active_count'] for row in results),
            'expired_memories': sum(row['expired_count'] for row in results)
        }
        
        return stats
    
    def search_memories(
        self, 
        user_id: str, 
        query_text: str, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search memories using full-text search
        
        Args:
            user_id: User identifier
            query_text: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching memory dictionaries
        """
        query = """
            SELECT 
                memory_id, 
                kind, 
                text, 
                importance, 
                created_at, 
                expires_at,
                ts_rank(to_tsvector('english', text), plainto_tsquery('english', %s)) as rank
            FROM app.memories
            WHERE user_id = %s
            AND (expires_at IS NULL OR expires_at > NOW())
            AND to_tsvector('english', text) @@ plainto_tsquery('english', %s)
            ORDER BY rank DESC, importance DESC
            LIMIT %s
        """
        
        return db.execute_query(query, (query_text, user_id, query_text, limit))


# Singleton instance
_memory_storage = None

def get_memory_storage() -> MemoryStorage:
    """Get singleton instance of MemoryStorage"""
    global _memory_storage
    if _memory_storage is None:
        _memory_storage = MemoryStorage()
    return _memory_storage
