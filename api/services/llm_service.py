"""
LLM Service

Handles LLM integration for response generation using OpenAI.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from api.utils.config import settings
from api.utils.demo_logger import log_llm_prompt

logger = logging.getLogger(__name__)


class LLMService:
    """Handles LLM integration for response generation using OpenAI"""
    
    def __init__(self):
        self.model = settings.LLM_MODEL
        self.default_max_tokens = settings.LLM_MAX_TOKENS
        self.default_temperature = settings.LLM_TEMPERATURE
        
        # Initialize OpenAI client
        self._init_openai()
    
    def _init_openai(self):
        """Initialize OpenAI client"""
        try:
            import openai
            self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("OpenAI client initialized")
        except ImportError:
            logger.error("OpenAI package not installed")
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.client = None
    
    def generate_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate response using OpenAI LLM
        
        Args:
            prompt: Complete prompt with context
            context: Optional additional context
            max_tokens: Optional max tokens override (uses default if not provided)
            temperature: Optional temperature override (uses default if not provided)
            
        Returns:
            Dictionary containing response and metadata
        """
        if not self.client:
            return self._fallback_response(prompt, context)
        
        # Use provided parameters or fall back to defaults
        max_tokens = max_tokens if max_tokens is not None else self.default_max_tokens
        temperature = temperature if temperature is not None else self.default_temperature
        
        # Log prompt for demo purposes (non-blocking)
        try:
            session_id = (context or {}).get('session_id') if isinstance(context, dict) else None
            user_id = (context or {}).get('user_id') if isinstance(context, dict) else None
            log_llm_prompt(
                prompt=prompt,
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                session_id=str(session_id) if session_id else None,
                user_id=user_id,
                context=context or {}
            )
        except Exception:
            pass

        try:
            return self._generate_openai_response(prompt, context, max_tokens, temperature)
        
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._fallback_response(prompt, context)
    
    def _generate_openai_response(
        self, 
        prompt: str, 
        context: Optional[Dict[str, Any]], 
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate response using OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            content = response.choices[0].message.content
            usage = response.usage
            
            return {
                'response': content,
                'provider': 'openai',
                'model': self.model,
                'usage': {
                    'prompt_tokens': usage.prompt_tokens,
                    'completion_tokens': usage.completion_tokens,
                    'total_tokens': usage.total_tokens
                },
                'metadata': {
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'context_used': context is not None
                }
            }
        
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return self._fallback_response(prompt, context)
    
    def _fallback_response(self, prompt: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback response when LLM is not available"""
        
        # Extract key information from prompt
        response_parts = []
        
        # Check for business context
        if context and context.get('business_context'):
            business_context = context['business_context']
            response_parts.append("Based on the business context available:")
            
            for entity_name, entity_data in business_context.items():
                if isinstance(entity_data, dict):
                    if 'customer' in entity_data:
                        customer = entity_data['customer']
                        response_parts.append(f"- {entity_name} is a {customer.get('industry', 'Unknown')} customer")
                    
                    if 'orders' in entity_data:
                        orders = entity_data['orders']
                        response_parts.append(f"- {entity_name} has {len(orders)} orders")
                    
                    if 'invoices' in entity_data:
                        invoices = entity_data['invoices']
                        response_parts.append(f"- {entity_name} has {len(invoices)} invoices")
        
        # Check for memories
        if context and context.get('memories'):
            memories = context['memories']
            response_parts.append(f"\nI found {len(memories)} relevant memories from previous conversations.")
            
            # Show most important memories
            important_memories = [m for m in memories if m.get('importance', 0) > 0.7]
            if important_memories:
                response_parts.append("Key memories:")
                for memory in important_memories[:3]:
                    response_parts.append(f"- {memory['text']}")
        
        # Check for semantic triples
        if context and context.get('semantic_triples'):
            triples = context['semantic_triples']
            response_parts.append(f"\nI have {len(triples)} pieces of knowledge about relationships and facts.")
        
        # Add basic response
        if not response_parts:
            response_parts.append("I understand your query, but I'm currently unable to access the full LLM service.")
            response_parts.append("I can help you with basic information about the business context available.")
        
        response_parts.append("\nFor a complete response, please ensure the LLM service is properly configured.")
        
        return {
            'response': '\n'.join(response_parts),
            'provider': 'fallback',
            'model': 'fallback',
            'usage': {
                'prompt_tokens': len(prompt),
                'completion_tokens': len('\n'.join(response_parts)),
                'total_tokens': len(prompt) + len('\n'.join(response_parts))
            },
            'metadata': {
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'context_used': context is not None,
                'fallback': True
            }
        }
    
    def generate_memory_summary(
        self, 
        memories: List[Dict[str, Any]], 
        user_id: str
    ) -> str:
        """
        Generate a summary of memories for consolidation
        
        Args:
            memories: List of memories to summarize
            user_id: User identifier
            
        Returns:
            Summary text
        """
        if not memories:
            return "No memories to summarize."
        
        # Group memories by type
        memories_by_type = {}
        for memory in memories:
            memory_type = memory['kind']
            if memory_type not in memories_by_type:
                memories_by_type[memory_type] = []
            memories_by_type[memory_type].append(memory)
        
        summary_parts = [f"Memory Summary for User {user_id}:"]
        
        for memory_type, type_memories in memories_by_type.items():
            summary_parts.append(f"\n{memory_type.title()} Memories ({len(type_memories)} total):")
            
            # Sort by importance
            sorted_memories = sorted(type_memories, key=lambda x: x.get('importance', 0), reverse=True)
            
            for memory in sorted_memories[:5]:  # Show top 5 per type
                memory_text = memory['text']
                importance = memory.get('importance', 0)
                summary_parts.append(f"- {memory_text} (Importance: {importance:.2f})")
            
            if len(sorted_memories) > 5:
                summary_parts.append(f"- ... and {len(sorted_memories) - 5} more {memory_type} memories")
        
        return '\n'.join(summary_parts)
    
    def extract_action_items(self, response: str) -> List[Dict[str, Any]]:
        """
        Extract action items from LLM response
        
        Args:
            response: LLM response text
            
        Returns:
            List of action item dictionaries
        """
        action_items = []
        
        # Look for action item patterns
        action_patterns = [
            r'Action item:\s*(.+)',
            r'Todo:\s*(.+)',
            r'Follow up:\s*(.+)',
            r'Next step:\s*(.+)',
            r'Need to:\s*(.+)'
        ]
        
        import re
        for pattern in action_patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                action_text = match.group(1).strip()
                action_items.append({
                    'text': action_text,
                    'extracted_at': datetime.now(timezone.utc).isoformat(),
                    'confidence': 0.8
                })
        
        return action_items
    
    def validate_response(self, response: str) -> Dict[str, Any]:
        """
        Validate LLM response for quality and completeness
        
        Args:
            response: LLM response text
            
        Returns:
            Validation results dictionary
        """
        validation_results = {
            'is_valid': True,
            'issues': [],
            'suggestions': []
        }
        
        # Check response length
        if len(response) < 10:
            validation_results['is_valid'] = False
            validation_results['issues'].append("Response too short")
        
        # Check for common issues
        if response.lower().strip() in ['', 'n/a', 'none', 'null']:
            validation_results['is_valid'] = False
            validation_results['issues'].append("Empty or placeholder response")
        
        # Check for helpfulness indicators
        helpful_indicators = ['based on', 'according to', 'here is', 'i found', 'the data shows']
        if not any(indicator in response.lower() for indicator in helpful_indicators):
            validation_results['suggestions'].append("Consider adding more context references")
        
        # Check for actionability
        action_indicators = ['you can', 'next step', 'action item', 'follow up', 'recommend']
        if not any(indicator in response.lower() for indicator in action_indicators):
            validation_results['suggestions'].append("Consider adding actionable next steps")
        
        return validation_results


# Singleton instance
_llm_service = None

def get_llm_service() -> LLMService:
    """Get singleton instance of LLMService"""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
