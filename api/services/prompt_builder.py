"""
Prompt Builder Service

Structures context as semantic triples for LLM consumption.
Creates well-formatted prompts with business context and memory integration.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from api.utils.config import settings

logger = logging.getLogger(__name__)


class PromptBuilder:
    """Builds structured prompts with semantic triples for LLM consumption"""
    
    def __init__(self):
        self.max_context_length = 4000  # Maximum context length in characters
        self.max_triples = 50  # Maximum number of triples to include
        self.max_memories = 20  # Maximum number of memories to include
    
    def build_prompt(
        self, 
        user_query: str, 
        synthesized_context: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Build a complete prompt with context and semantic triples
        
        Args:
            user_query: User's query
            synthesized_context: Context from retrieval and synthesis
            system_prompt: Optional custom system prompt
            
        Returns:
            Formatted prompt string
        """
        if not system_prompt:
            system_prompt = self._get_default_system_prompt()
        
        # Extract components from synthesized context
        memories = synthesized_context.get('memories', [])
        business_context = synthesized_context.get('business_context', {})
        relationships = synthesized_context.get('relationships', [])
        semantic_triples = synthesized_context.get('semantic_triples', [])
        
        # Build context sections
        context_sections = []
        
        # 1. Business Context Section
        if business_context:
            business_section = self._build_business_context_section(business_context)
            if business_section:
                context_sections.append(business_section)
        
        # 2. Memory Context Section
        if memories:
            memory_section = self._build_memory_context_section(memories)
            if memory_section:
                context_sections.append(memory_section)
        
        # 3. Semantic Relationships Section
        if relationships:
            relationships_section = self._build_relationships_section(relationships)
            if relationships_section:
                context_sections.append(relationships_section)
        
        # 4. Semantic Triples Section
        if semantic_triples:
            triples_section = self._build_semantic_triples_section(semantic_triples)
            if triples_section:
                context_sections.append(triples_section)
        
        # Combine all sections
        context_text = "\n\n".join(context_sections)
        
        # Build final prompt with user query at the beginning
        prompt = f"{system_prompt}\n\nUser Query: {user_query}\n\n{context_text}"
        
        # Truncate if too long
        if len(prompt) > self.max_context_length:
            prompt = self._truncate_prompt(prompt, user_query)
        
        return prompt
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt"""
        return """You are an intelligent assistant with access to business context and memory. You can help users with:

1. Business queries about customers, orders, invoices, and work orders
2. Memory-based assistance using previous conversations
3. Semantic understanding of business relationships

Key capabilities:
- Access to real-time business data (customers, orders, invoices)
- Memory of previous conversations and user preferences
- Understanding of business relationships and context
- Ability to provide specific, actionable information

When responding:
- Use the provided business context to give accurate information
- Reference relevant memories when appropriate
- Be specific about data sources (e.g., "According to your order history...")
- Ask clarifying questions when needed
- Provide actionable next steps when possible"""
    
    def _build_business_context_section(self, business_context: Dict[str, Any]) -> str:
        """Build business context section"""
        if not business_context:
            return ""
        
        section_parts = ["## Business Context"]
        
        for entity_name, context in business_context.items():
            if isinstance(context, dict):
                # Customer context
                if 'customer' in context:
                    customer = context['customer']
                    section_parts.append(f"**{entity_name} (Customer)**")
                    section_parts.append(f"- Industry: {customer.get('industry', 'Unknown')}")
                    section_parts.append(f"- Status: {customer.get('status', 'Unknown')}")
                
                # Order context
                if 'orders' in context:
                    orders = context['orders']
                    section_parts.append(f"- Orders ({len(orders)} total):")
                    for order in orders[:3]:  # Show first 3 orders
                        section_parts.append(f"  - {order.get('so_number', 'Unknown')}: {order.get('status', 'Unknown')} (${order.get('total_amount', 0)})")
                    if len(orders) > 3:
                        section_parts.append(f"  - ... and {len(orders) - 3} more orders")
                
                # Invoice context
                if 'invoices' in context:
                    invoices = context['invoices']
                    section_parts.append(f"- Invoices ({len(invoices)} total):")
                    for invoice in invoices[:3]:  # Show first 3 invoices
                        section_parts.append(f"  - {invoice.get('invoice_number', 'Unknown')}: ${invoice.get('amount', 0)} ({invoice.get('status', 'Unknown')})")
                    if len(invoices) > 3:
                        section_parts.append(f"  - ... and {len(invoices) - 3} more invoices")
                
                # Financial summary
                if 'summary' in context:
                    summary = context['summary']
                    section_parts.append(f"- Financial Summary:")
                    section_parts.append(f"  - Total Orders: {summary.get('total_orders', 0)}")
                    section_parts.append(f"  - Open Invoices: {summary.get('open_invoices', 0)}")
                    section_parts.append(f"  - Total Open Amount: ${summary.get('total_open_amount', 0)}")
                
                section_parts.append("")  # Empty line between entities
        
        return "\n".join(section_parts)
    
    def _build_memory_context_section(self, memories: List[Dict[str, Any]]) -> str:
        """Build memory context section"""
        if not memories:
            return ""
        
        # Group memories by type
        memories_by_type = {}
        for memory in memories:
            memory_type = memory['kind']
            if memory_type not in memories_by_type:
                memories_by_type[memory_type] = []
            memories_by_type[memory_type].append(memory)
        
        section_parts = ["## Relevant Memories"]
        
        # Add memories by type
        for memory_type, type_memories in memories_by_type.items():
            section_parts.append(f"### {memory_type.title()} Memories")
            
            for memory in type_memories[:5]:  # Limit to 5 per type
                memory_text = memory['text']
                importance = memory['importance']
                created_at = memory.get('created_at', 'Unknown')
                
                # Format memory with metadata
                section_parts.append(f"- {memory_text} (Importance: {importance:.2f}, Created: {created_at})")
            
            if len(type_memories) > 5:
                section_parts.append(f"- ... and {len(type_memories) - 5} more {memory_type} memories")
            
            section_parts.append("")  # Empty line between types
        
        return "\n".join(section_parts)
    
    def _build_relationships_section(self, relationships: List[Dict[str, Any]]) -> str:
        """Build relationships section"""
        if not relationships:
            return ""
        
        section_parts = ["## Semantic Relationships"]
        
        for relationship in relationships[:10]:  # Limit to 10 relationships
            subject = relationship.get('subject', 'Unknown')
            predicate = relationship.get('predicate', 'Unknown')
            object_val = relationship.get('object', 'Unknown')
            confidence = relationship.get('confidence', 0.0)
            
            section_parts.append(f"- {subject} {predicate} {object_val} (Confidence: {confidence:.2f})")
        
        if len(relationships) > 10:
            section_parts.append(f"- ... and {len(relationships) - 10} more relationships")
        
        return "\n".join(section_parts)
    
    def _build_semantic_triples_section(self, semantic_triples: List[Dict[str, Any]]) -> str:
        """Build semantic triples section"""
        if not semantic_triples:
            return ""
        
        section_parts = ["## Knowledge Graph"]
        
        # Group triples by subject
        triples_by_subject = {}
        for triple in semantic_triples:
            subject = triple.get('subject', 'Unknown')
            if subject not in triples_by_subject:
                triples_by_subject[subject] = []
            triples_by_subject[subject].append(triple)
        
        for subject, subject_triples in triples_by_subject.items():
            section_parts.append(f"### {subject}")
            
            for triple in subject_triples[:5]:  # Limit to 5 per subject
                predicate = triple.get('predicate', 'Unknown')
                object_val = triple.get('object', 'Unknown')
                source = triple.get('source', 'Unknown')
                confidence = triple.get('confidence', 0.0)
                
                section_parts.append(f"- {predicate}: {object_val} (Source: {source}, Confidence: {confidence:.2f})")
            
            if len(subject_triples) > 5:
                section_parts.append(f"- ... and {len(subject_triples) - 5} more relationships")
            
            section_parts.append("")  # Empty line between subjects
        
        return "\n".join(section_parts)
    
    def _truncate_prompt(self, prompt: str, user_query: str) -> str:
        """Truncate prompt if it's too long"""
        # Keep system prompt and user query (which now appear first)
        system_prompt = self._get_default_system_prompt()
        # User query now appears right after system prompt, so calculate up to end of user query
        user_query_section = f"{system_prompt}\n\nUser Query: {user_query}"
        min_length = len(user_query_section) + 100  # Buffer
        
        if len(prompt) <= min_length:
            return prompt
        
        # Calculate available space for context
        available_space = self.max_context_length - min_length
        
        # Find where context sections start (they come after user query now)
        context_start = prompt.find("## Business Context")
        if context_start == -1:
            context_start = prompt.find("## Relevant Memories")
        
        if context_start == -1:
            context_start = prompt.find("## Semantic Relationships")
        
        if context_start == -1:
            context_start = prompt.find("## Knowledge Graph")
        
        if context_start != -1:
            context_section = prompt[context_start:]
            if len(context_section) > available_space:
                context_section = context_section[:available_space] + "\n\n[Context truncated...]"
            
            prompt = prompt[:context_start] + context_section
        
        return prompt
    
    def build_memory_prompt(
        self, 
        user_query: str, 
        memories: List[Dict[str, Any]],
        system_prompt: Optional[str] = None
    ) -> str:
        """Build a prompt focused on memory context"""
        if not system_prompt:
            system_prompt = self._get_default_system_prompt()
        
        if not memories:
            return f"{system_prompt}\n\nUser Query: {user_query}"
        
        # Build memory context
        memory_context = self._build_memory_context_section(memories)
        
        # Combine with user query at the beginning
        prompt = f"{system_prompt}\n\nUser Query: {user_query}\n\n{memory_context}"
        
        return prompt
    
    def build_business_prompt(
        self, 
        user_query: str, 
        business_context: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> str:
        """Build a prompt focused on business context"""
        if not system_prompt:
            system_prompt = self._get_default_system_prompt()
        
        if not business_context:
            return f"{system_prompt}\n\nUser Query: {user_query}"
        
        # Build business context
        business_section = self._build_business_context_section(business_context)
        
        # Combine with user query at the beginning
        prompt = f"{system_prompt}\n\nUser Query: {user_query}\n\n{business_section}"
        
        return prompt
    
    def format_semantic_triples(self, triples: List[Dict[str, Any]]) -> str:
        """Format semantic triples as readable text"""
        if not triples:
            return "No semantic triples available."
        
        formatted_triples = []
        for triple in triples:
            subject = triple.get('subject', 'Unknown')
            predicate = triple.get('predicate', 'Unknown')
            object_val = triple.get('object', 'Unknown')
            confidence = triple.get('confidence', 0.0)
            
            formatted_triples.append(f"• {subject} {predicate} {object_val} (Confidence: {confidence:.2f})")
        
        return "\n".join(formatted_triples)
    
    def get_context_summary(self, synthesized_context: Dict[str, Any]) -> str:
        """Get a summary of the context for logging/debugging"""
        memories = synthesized_context.get('memories', [])
        business_context = synthesized_context.get('business_context', {})
        relationships = synthesized_context.get('relationships', [])
        semantic_triples = synthesized_context.get('semantic_triples', [])
        
        summary_parts = []
        
        if memories:
            summary_parts.append(f"{len(memories)} memories")
        
        if business_context:
            summary_parts.append(f"{len(business_context)} business entities")
        
        if relationships:
            summary_parts.append(f"{len(relationships)} relationships")
        
        if semantic_triples:
            summary_parts.append(f"{len(semantic_triples)} semantic triples")
        
        return ", ".join(summary_parts) if summary_parts else "No context available"


# Singleton instance
_prompt_builder = None

def get_prompt_builder() -> PromptBuilder:
    """Get singleton instance of PromptBuilder"""
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = PromptBuilder()
    return _prompt_builder
