"""
Chat endpoint for processing user messages with memory integration
"""

from fastapi import APIRouter, HTTPException
from api.models.api import ChatRequest, ChatResponse
from api.services.entity_extractor import get_entity_extractor
from api.services.semantic_relationships import get_semantic_relationship_builder
from api.services.memory_vectorizer import get_memory_vectorizer
from api.services.memory_storage import get_memory_storage
from api.services.retrieval_synthesis import RetrievalSynthesis
from api.services.prompt_builder import get_prompt_builder
from api.services.llm_service import get_llm_service
from api.utils.database import db
import uuid
import logging
import time

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize singleton services
entity_extractor = get_entity_extractor()
relationship_builder = get_semantic_relationship_builder()
memory_vectorizer = get_memory_vectorizer()
memory_storage = get_memory_storage()
retrieval_synthesis = RetrievalSynthesis()
prompt_builder = get_prompt_builder()
llm_service = get_llm_service()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Process chat message with full memory pipeline:
    1. Extract entities
    2. Retrieve context (memories + business data + relationships)
    3. Generate LLM response
    4. Store assistant message and create memories
    """
    start_time = time.time()
    
    # Get the latest user message from the messages list
    user_messages = [msg for msg in request.messages if msg.role == 'user']
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user messages found in request")
    
    user_message = user_messages[-1].content  # Use the last user message
    user_id = request.user_id or "anonymous"
    session_id = request.session_id or uuid.uuid4()
    
    try:
        # Step 1: Extract entities from user message
        entities = entity_extractor.extract_entities(
            user_message, 
            user_id, 
            str(session_id)
        )
        logger.info(f"Extracted {len(entities)} entities")
        
        # Store entities in database
        entity_ids = entity_extractor.store_entities(entities)
        
        # Step 2: Build semantic relationships from conversation
        conv_relationships = relationship_builder.extract_conversational_relationships(
            user_message, entities
        )
        if conv_relationships:
            relationship_builder.store_relationships(conv_relationships)
            logger.info(f"Created {len(conv_relationships)} conversational relationships")
        
        # Step 3: Retrieve and synthesize context
        synthesized_context = retrieval_synthesis.retrieve_and_synthesize(
            user_message,
            user_id,
            entities,
            max_memories=request.max_memories if request.retrieve_memories else 0,
            include_business_context=True
        )
        
        # Step 4: Build prompt with structured context
        prompt = prompt_builder.build_prompt(
            user_query=user_message,
            synthesized_context=synthesized_context
        )
        
        # Step 5: Generate LLM response
        llm_response = llm_service.generate_response(
            prompt=prompt,
            context=synthesized_context
        )
        
        # Extract the assistant message from LLM response
        assistant_message = llm_response.get('response', '')
        logger.info(f"Generated LLM response: {len(assistant_message)} chars")
        
        # Step 6: Create memories from conversation turn
        memories = []
        memories_created = 0
        
        if request.create_memories:
            memories = memory_vectorizer.analyze_conversation_turn(
                user_message=user_message,
                assistant_message=assistant_message,
                entities=entities,
                session_id=str(session_id),
                user_id=user_id
            )
            
            # Step 7: Store memories with PII redaction
            if memories:
                memory_ids = memory_storage.store_memories(
                    memories=memories,
                    session_id=str(session_id),
                    user_id=user_id
                )
                memories_created = len(memory_ids)
                logger.info(f"Stored {memories_created} memories")
        
        # Create ChatResponse matching the model
        from api.models.api import InjectedContext
        
        injected_context = InjectedContext(
            memories=[],
            entities=[],
            domain_facts=[],
            semantic_triples=[]
        )
        
        return ChatResponse(
            response=assistant_message,
            session_id=session_id,
            injected_context=injected_context,
            memories_created=memories_created,
            entities_linked=len(entities),
            usage=llm_response.get('usage')
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

