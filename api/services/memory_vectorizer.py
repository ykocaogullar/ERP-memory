"""
Memory Vectorizer Service

Analyzes conversation turns and extracts memory-worthy facts.
Converts conversational context into structured memories with embeddings.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from api.utils.database import db
from api.utils.config import settings
from api.services.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class MemoryVectorizer:
    """Converts conversational context into structured memories with embeddings"""
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        
        # Memory extraction patterns
        self.memory_patterns = {
            'preference': [
                r'prefer(?:s)?\s+(.+)',
                r'likes?\s+(.+)',
                r'wants?\s+(.+)'
            ],
            'requirement': [
                r'require(?:s)?\s+(.+)',
                r'needs?\s+(.+)',
                r'must\s+(.+)'
            ],
            'policy': [
                r'policy\s+(.+)',
                r'rule\s+(.+)',
                r'always\s+(.+)',
                r'never\s+(.+)'
            ],
            'commitment': [
                r'promise(?:s)?\s+(.+)',
                r'commit(?:s)?\s+(.+)',
                r'agree(?:s)?\s+(.+)'
            ],
            'fact': [
                r'remember\s+(.+)',
                r'note\s+(.+)',
                r'keep in mind\s+(.+)'
            ]
        }
        
        # Importance keywords
        self.importance_keywords = {
            'high': ['urgent', 'critical', 'important', 'must', 'always', 'never'],
            'medium': ['prefer', 'like', 'want', 'need', 'should'],
            'low': ['maybe', 'perhaps', 'might', 'could']
        }
    
    def analyze_conversation_turn(
        self, 
        user_message: str, 
        assistant_message: str, 
        entities: List[Dict[str, Any]],
        session_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Analyze a conversation turn and extract memory-worthy facts
        
        Args:
            user_message: User's input message
            assistant_message: Assistant's response
            entities: Extracted entities from the conversation
            session_id: Session identifier
            user_id: User identifier
            
        Returns:
            List of memory dictionaries ready for storage
        """
        memories = []
        
        # 1. Extract episodic memory (what happened)
        episodic_memory = self._extract_episodic_memory(
            user_message, assistant_message, entities, session_id, user_id
        )
        if episodic_memory:
            memories.append(episodic_memory)
        
        # 2. Extract semantic memories (facts, preferences, policies)
        semantic_memories = self._extract_semantic_memories(
            user_message, entities, session_id, user_id
        )
        memories.extend(semantic_memories)
        
        # 3. Extract profile memories (user/entity characteristics)
        profile_memories = self._extract_profile_memories(
            user_message, entities, session_id, user_id
        )
        memories.extend(profile_memories)
        
        # 4. Extract commitment memories (promises, agreements)
        commitment_memories = self._extract_commitment_memories(
            user_message, entities, session_id, user_id
        )
        memories.extend(commitment_memories)
        
        # 5. Extract todo memories (action items)
        todo_memories = self._extract_todo_memories(
            user_message, assistant_message, entities, session_id, user_id
        )
        memories.extend(todo_memories)
        
        logger.info(f"Extracted {len(memories)} memories from conversation turn")
        return memories
    
    def _extract_episodic_memory(
        self, 
        user_message: str, 
        assistant_message: str, 
        entities: List[Dict[str, Any]],
        session_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Extract episodic memory (what happened in this conversation)"""
        
        # Create a summary of the conversation turn
        entity_names = [e['name'] for e in entities if e.get('name')]
        entity_context = f" involving {', '.join(entity_names)}" if entity_names else ""
        
        episodic_text = f"User asked about {user_message[:100]}{entity_context}. Assistant provided response about {assistant_message[:100]}"
        
        # Generate embedding
        embedding = self.embedding_service.embed_text(episodic_text) if settings.ENABLE_VECTORS else None
        
        # Calculate importance based on entities and content
        importance = self._calculate_importance(episodic_text, entities, 'episodic')
        
        return {
            'kind': 'episodic',
            'text': episodic_text,
            'embedding': embedding,
            'importance': importance,
            'ttl_days': 30,  # Episodic memories expire after 30 days
            'provenance': {
                'source': 'conversation',
                'entities': [e['name'] for e in entities],
                'user_message_length': len(user_message),
                'assistant_message_length': len(assistant_message),
                'confidence': 0.8
            },
            'session_id': session_id,
            'user_id': user_id
        }
    
    def _extract_semantic_memories(
        self, 
        user_message: str, 
        entities: List[Dict[str, Any]],
        session_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Extract semantic memories (facts, preferences, policies)"""
        memories = []
        
        for memory_type, patterns in self.memory_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, user_message, re.IGNORECASE)
                for match in matches:
                    # Extract the memory content
                    content = match.group(1).strip()
                    
                    # Find relevant entities
                    relevant_entities = self._find_relevant_entities(entities, user_message, match.start())
                    
                    # Create memory text
                    if relevant_entities:
                        entity_names = [e['name'] for e in relevant_entities]
                        memory_text = f"{', '.join(entity_names)} {memory_type}: {content}"
                    else:
                        memory_text = f"{memory_type}: {content}"
                    
                    # Generate embedding
                    embedding = self.embedding_service.embed_text(memory_text) if settings.ENABLE_VECTORS else None
                    
                    # Calculate importance
                    importance = self._calculate_importance(memory_text, relevant_entities, memory_type)
                    
                    memories.append({
                        'kind': 'semantic',
                        'text': memory_text,
                        'embedding': embedding,
                        'importance': importance,
                        'ttl_days': None,  # Semantic memories don't expire
                        'provenance': {
                            'source': 'conversation',
                            'pattern': pattern,
                            'entities': [e['name'] for e in relevant_entities],
                            'confidence': 0.9
                        },
                        'session_id': session_id,
                        'user_id': user_id
                    })
        
        return memories
    
    def _extract_profile_memories(
        self, 
        user_message: str, 
        entities: List[Dict[str, Any]],
        session_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Extract profile memories (user/entity characteristics)"""
        memories = []
        
        # Look for profile-related patterns
        profile_patterns = [
            r'(\w+)\s+is\s+(.+)',
            r'(\w+)\s+has\s+(.+)',
            r'(\w+)\s+works\s+(.+)',
            r'(\w+)\s+specializes\s+(.+)'
        ]
        
        for pattern in profile_patterns:
            matches = re.finditer(pattern, user_message, re.IGNORECASE)
            for match in matches:
                entity_name = match.group(1)
                characteristic = match.group(2).strip()
                
                # Check if entity is in our extracted entities
                relevant_entity = next((e for e in entities if e['name'].lower() == entity_name.lower()), None)
                
                if relevant_entity:
                    memory_text = f"{entity_name} profile: {characteristic}"
                    embedding = self.embedding_service.embed_text(memory_text) if settings.ENABLE_VECTORS else None
                    
                    memories.append({
                        'kind': 'profile',
                        'text': memory_text,
                        'embedding': embedding,
                        'importance': 0.7,
                        'ttl_days': None,  # Profile memories don't expire
                        'provenance': {
                            'source': 'conversation',
                            'entity': entity_name,
                            'confidence': 0.8
                        },
                        'session_id': session_id,
                        'user_id': user_id
                    })
        
        return memories
    
    def _extract_commitment_memories(
        self, 
        user_message: str, 
        entities: List[Dict[str, Any]],
        session_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Extract commitment memories (promises, agreements)"""
        memories = []
        
        commitment_patterns = [
            r'will\s+(.+)',
            r'promise\s+(.+)',
            r'commit\s+(.+)',
            r'agree\s+(.+)',
            r'guarantee\s+(.+)'
        ]
        
        for pattern in commitment_patterns:
            matches = re.finditer(pattern, user_message, re.IGNORECASE)
            for match in matches:
                commitment = match.group(1).strip()
                
                # Find relevant entities
                relevant_entities = self._find_relevant_entities(entities, user_message, match.start())
                
                if relevant_entities:
                    entity_names = [e['name'] for e in relevant_entities]
                    memory_text = f"Commitment for {', '.join(entity_names)}: {commitment}"
                else:
                    memory_text = f"Commitment: {commitment}"
                
                embedding = self.embedding_service.embed_text(memory_text) if settings.ENABLE_VECTORS else None
                
                memories.append({
                    'kind': 'commitment',
                    'text': memory_text,
                    'embedding': embedding,
                    'importance': 0.9,  # Commitments are high importance
                    'ttl_days': 90,  # Commitments expire after 90 days
                    'provenance': {
                        'source': 'conversation',
                        'entities': [e['name'] for e in relevant_entities],
                        'confidence': 0.95
                    },
                    'session_id': session_id,
                    'user_id': user_id
                })
        
        return memories
    
    def _extract_todo_memories(
        self, 
        user_message: str, 
        assistant_message: str, 
        entities: List[Dict[str, Any]],
        session_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Extract todo memories (action items)"""
        memories = []
        
        todo_patterns = [
            r'need to\s+(.+)',
            r'should\s+(.+)',
            r'must\s+(.+)',
            r'action item:\s*(.+)',
            r'todo:\s*(.+)',
            r'follow up\s+(.+)'
        ]
        
        # Check both user and assistant messages for todos
        for text, source in [(user_message, 'user'), (assistant_message, 'assistant')]:
            for pattern in todo_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    todo_item = match.group(1).strip()
                    
                    # Find relevant entities
                    relevant_entities = self._find_relevant_entities(entities, text, match.start())
                    
                    if relevant_entities:
                        entity_names = [e['name'] for e in relevant_entities]
                        memory_text = f"Todo for {', '.join(entity_names)}: {todo_item}"
                    else:
                        memory_text = f"Todo: {todo_item}"
                    
                    embedding = self.embedding_service.embed_text(memory_text) if settings.ENABLE_VECTORS else None
                    
                    memories.append({
                        'kind': 'todo',
                        'text': memory_text,
                        'embedding': embedding,
                        'importance': 0.8,
                        'ttl_days': 14,  # Todos expire after 14 days
                        'provenance': {
                            'source': source,
                            'entities': [e['name'] for e in relevant_entities],
                            'confidence': 0.85
                        },
                        'session_id': session_id,
                        'user_id': user_id
                    })
        
        return memories
    
    def _find_relevant_entities(
        self, 
        entities: List[Dict[str, Any]], 
        text: str, 
        position: int
    ) -> List[Dict[str, Any]]:
        """Find entities most relevant to a specific position in text"""
        if not entities:
            return []
        
        # Find entities mentioned near the position
        relevant_entities = []
        for entity in entities:
            entity_name = entity['name']
            # Find all occurrences of the entity name
            for match in re.finditer(re.escape(entity_name), text, re.IGNORECASE):
                # Check if the occurrence is near our position (within 50 characters)
                if abs(match.start() - position) <= 50:
                    relevant_entities.append(entity)
                    break
        
        return relevant_entities
    
    def _calculate_importance(
        self, 
        text: str, 
        entities: List[Dict[str, Any]], 
        memory_type: str
    ) -> float:
        """Calculate importance score for a memory"""
        base_score = 0.5
        
        # Base score by memory type
        type_weights = {
            'commitment': 0.9,
            'policy': 0.85,
            'semantic': 0.7,
            'profile': 0.6,
            'todo': 0.8,
            'episodic': 0.4
        }
        base_score = type_weights.get(memory_type, 0.5)
        
        # Boost for entities
        if entities:
            base_score += 0.1
            # Extra boost for customer entities
            if any(e.get('type') == 'customer' for e in entities):
                base_score += 0.1
        
        # Boost for importance keywords
        text_lower = text.lower()
        for level, keywords in self.importance_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                if level == 'high':
                    base_score += 0.2
                elif level == 'medium':
                    base_score += 0.1
                elif level == 'low':
                    base_score += 0.05
                break
        
        # Boost for longer, more detailed memories
        if len(text) > 100:
            base_score += 0.05
        
        return min(base_score, 1.0)
    
    def consolidate_memories(
        self, 
        memories: List[Dict[str, Any]], 
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Consolidate similar memories to avoid duplication
        
        Args:
            memories: List of memory dictionaries
            user_id: User identifier
            
        Returns:
            List of consolidated memories
        """
        if len(memories) <= 1:
            return memories
        
        # Group memories by kind
        memories_by_kind = {}
        for memory in memories:
            kind = memory['kind']
            if kind not in memories_by_kind:
                memories_by_kind[kind] = []
            memories_by_kind[kind].append(memory)
        
        consolidated = []
        
        for kind, kind_memories in memories_by_kind.items():
            if len(kind_memories) == 1:
                consolidated.extend(kind_memories)
                continue
            
            # For multiple memories of same kind, keep the most important one
            # and merge others into it
            sorted_memories = sorted(kind_memories, key=lambda x: x['importance'], reverse=True)
            primary_memory = sorted_memories[0]
            
            # Merge additional details from other memories
            if len(sorted_memories) > 1:
                additional_details = []
                for memory in sorted_memories[1:]:
                    # Extract unique information from secondary memories
                    if memory['text'] != primary_memory['text']:
                        additional_details.append(memory['text'])
                
                if additional_details:
                    primary_memory['text'] += f" Also: {'; '.join(additional_details)}"
                    # Recalculate importance
                    primary_memory['importance'] = self._calculate_importance(
                        primary_memory['text'], 
                        primary_memory.get('provenance', {}).get('entities', []),
                        kind
                    )
            
            consolidated.append(primary_memory)
        
        logger.info(f"Consolidated {len(memories)} memories into {len(consolidated)}")
        return consolidated


# Singleton instance
_memory_vectorizer = None

def get_memory_vectorizer() -> MemoryVectorizer:
    """Get singleton instance of MemoryVectorizer"""
    global _memory_vectorizer
    if _memory_vectorizer is None:
        _memory_vectorizer = MemoryVectorizer()
    return _memory_vectorizer
