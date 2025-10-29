"""
API route handlers

Includes:
- chat: Chat endpoint for processing messages
- memory: Memory management endpoints
- entities: Entity management endpoints  
- consolidate: Memory consolidation endpoints
- system: Health check and statistics
"""

from api.routes import chat, memory, entities, consolidate, system

__all__ = ["chat", "memory", "entities", "consolidate", "system"]
