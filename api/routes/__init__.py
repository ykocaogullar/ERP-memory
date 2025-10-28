"""
API route handlers

Includes:
- chat: Chat endpoint for processing messages
- memory: Memory management endpoints
- entities: Entity management endpoints  
- system: Health check and statistics
"""

from api.routes import chat, memory, entities, system

__all__ = ["chat", "memory", "entities", "system"]
