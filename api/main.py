"""
Main FastAPI application for ERP Memory System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import chat, memory, entities, system, consolidate
from api.utils.config import settings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="ERP Memory System API",
    description="Ontology-aware memory system for LLM agents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1", tags=["chat"])
app.include_router(memory.router, prefix="/api/v1", tags=["memory"])
app.include_router(entities.router, prefix="/api/v1", tags=["entities"])
app.include_router(consolidate.router, prefix="/api/v1", tags=["consolidation"])
app.include_router(system.router, tags=["system"])


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "ERP Memory System API",
        "version": "1.0.0",
        "endpoints": {
            "chat": "/api/v1/chat",
            "memory": "/api/v1/memory",
            "entities": "/api/v1/entities",
            "consolidate": "/api/v1/consolidate",
            "health": "/health",
            "stats": "/stats"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ERP Memory System"}

