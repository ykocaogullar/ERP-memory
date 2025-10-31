"""
Demo Logger Utility

Logs retrieval synthesis context to a file for demonstration purposes.
"""

import json
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
DEMO_LOG_DIR = PROJECT_ROOT / "demo"
DEMO_LOG_FILE = DEMO_LOG_DIR / "retrieval_synthesis.log"
LLM_PROMPTS_LOG_FILE = DEMO_LOG_DIR / "llm_prompts.log"


def ensure_demo_log_dir():
    """Ensure the demo log directory exists"""
    DEMO_LOG_DIR.mkdir(exist_ok=True)


def log_retrieval_synthesis(
    user_message: str,
    synthesized_context: Dict[str, Any],
    session_id: str = None,
    user_id: str = None
):
    """
    Log the synthesized context from retrieval_synthesis to a file
    
    Args:
        user_message: The user's query
        synthesized_context: The context returned by retrieve_and_synthesize
        session_id: Optional session ID
        user_id: Optional user ID
    """
    ensure_demo_log_dir()
    
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'session_id': str(session_id) if session_id else None,
        'user_message': user_message,
        'synthesized_context': {
            'query': synthesized_context.get('query'),
            'summary': synthesized_context.get('summary'),
            'metadata': synthesized_context.get('metadata', {}),
            'memories_count': len(synthesized_context.get('memories', [])),
            'memories': synthesized_context.get('memories', []),
            'business_context': synthesized_context.get('business_context', {}),
            'relationships_count': len(synthesized_context.get('relationships', [])),
            'relationships': synthesized_context.get('relationships', []),
            'semantic_triples_count': len(synthesized_context.get('semantic_triples', [])),
            'semantic_triples': synthesized_context.get('semantic_triples', [])
        }
    }
    
    # Append to log file with pretty formatting
    try:
        with open(DEMO_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write("\n" + "="*80 + "\n")
            f.write(f"TIMESTAMP: {log_entry['timestamp']}\n")
            f.write(f"USER ID: {log_entry['user_id']}\n")
            f.write(f"SESSION ID: {log_entry['session_id']}\n")
            f.write(f"USER MESSAGE: {log_entry['user_message']}\n")
            f.write("-"*80 + "\n")
            f.write("SYNTHESIZED CONTEXT:\n")
            f.write("-"*80 + "\n")
            f.write(f"Summary: {log_entry['synthesized_context']['summary']}\n")
            f.write(f"\nMetadata:\n")
            f.write(json.dumps(log_entry['synthesized_context']['metadata'], indent=2))
            f.write(f"\n\nMemories ({log_entry['synthesized_context']['memories_count']}):\n")
            for i, memory in enumerate(log_entry['synthesized_context']['memories'], 1):
                f.write(f"  {i}. [{memory.get('kind', 'unknown')}] {memory.get('text', '')[:300]}\n")
            f.write(f"\nBusiness Context ({len(log_entry['synthesized_context']['business_context'])} entities):\n")
            for entity_name, context in log_entry['synthesized_context']['business_context'].items():
                f.write(f"  {entity_name}:\n")
                if isinstance(context, dict):
                    f.write(f"    {json.dumps(context, indent=6, default=str)}\n")
            f.write(f"\nRelationships ({log_entry['synthesized_context']['relationships_count']}):\n")
            for i, rel in enumerate(log_entry['synthesized_context']['relationships'], 1):
                f.write(f"  {i}. {rel.get('predicate', 'unknown')}: {rel.get('object_value', '')[:300]}\n")
            f.write(f"\nSemantic Triples ({log_entry['synthesized_context']['semantic_triples_count']}):\n")
            for i, triple in enumerate(log_entry['synthesized_context']['semantic_triples'][:20], 1):  # Limit to first 20
                f.write(f"  {i}. {triple.get('subject', '')} - {triple.get('predicate', '')} - {triple.get('object', '')}\n")
            if log_entry['synthesized_context']['semantic_triples_count'] > 20:
                f.write(f"  ... and {log_entry['synthesized_context']['semantic_triples_count'] - 20} more triples\n")
            f.write("="*80 + "\n")
    except Exception as e:
        # Don't fail the request if logging fails
        import logging
        logging.getLogger(__name__).error(f"Failed to write demo log: {e}")


def log_llm_prompt(
    prompt: str,
    model: str,
    max_tokens: int,
    temperature: float,
    session_id: str | None = None,
    user_id: str | None = None,
    context: Dict[str, Any] | None = None
):
    """Log the final prompt sent to the LLM to a separate demo log file."""
    ensure_demo_log_dir()
    timestamp = datetime.now().isoformat()
    try:
        safe_prompt = prompt if isinstance(prompt, str) else ""
        prompt_length = len(safe_prompt)
        if not safe_prompt.strip():
            safe_prompt_display = "[EMPTY PROMPT]"
        else:
            safe_prompt_display = safe_prompt
        with open(LLM_PROMPTS_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write("\n" + "="*80 + "\n")
            f.write(f"TIMESTAMP: {timestamp}\n")
            f.write(f"USER ID: {user_id}\n")
            f.write(f"SESSION ID: {session_id}\n")
            f.write(f"MODEL: {model}\n")
            f.write(f"PARAMS: max_tokens={max_tokens}, temperature={temperature}\n")
            # Basic context summary if available
            if isinstance(context, dict):
                meta = context.get('metadata', {})
                f.write("-"*80 + "\n")
                f.write("CONTEXT SUMMARY:\n")
                try:
                    summary_line = context.get('summary') or ''
                    f.write(f"Summary: {summary_line}\n")
                    counts = {
                        'memories': len(context.get('memories', []) or []),
                        'relationships': len(context.get('relationships', []) or []),
                        'semantic_triples': len(context.get('semantic_triples', []) or []),
                        'business_entities': len((context.get('business_context') or {}).keys())
                    }
                    f.write(json.dumps({'metadata': meta, 'counts': counts}, indent=2))
                    f.write("\n")
                except Exception:
                    pass
            f.write("-"*80 + "\n")
            f.write("PROMPT:\n")
            f.write(f"(length={prompt_length})\n")
            f.write("-"*80 + "\n")
            f.write(safe_prompt_display)
            f.write("\n" + "="*80 + "\n")
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to write LLM prompt log: {e}")


def clear_demo_log():
    """Clear the demo log file"""
    ensure_demo_log_dir()
    if DEMO_LOG_FILE.exists():
        DEMO_LOG_FILE.unlink()


def get_demo_log_path():
    """Get the path to the demo log file"""
    return str(DEMO_LOG_FILE)


