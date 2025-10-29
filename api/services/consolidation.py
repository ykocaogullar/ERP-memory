"""
Consolidation Service

Consolidates memories across session windows to create summaries.
Handles memory clustering, summarization, and session lifecycle management.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging

from api.utils.database import db
from api.services.embeddings import get_embedding_service
from api.services.llm_service import get_llm_service
from api.utils.config import settings

logger = logging.getLogger(__name__)


class ConsolidationService:
    """Consolidates memories across session windows"""

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.llm_service = get_llm_service()

    def consolidate_sessions(self, user_id: str, window_size: int = 3) -> Dict[str, Any]:
        """
        Consolidate last N sessions into summary
        
        Args:
            user_id: User to consolidate sessions for
            window_size: Number of recent sessions to consolidate
            
        Returns:
            Dict with consolidation results
        """
        logger.info(f"Starting consolidation for user {user_id}, window_size={window_size}")
        
        # Get recent unconsolidated sessions
        sessions_query = """
            SELECT DISTINCT session_id, started_at
            FROM app.sessions
            WHERE user_id = %s
            AND consolidated = false
            ORDER BY started_at DESC
            LIMIT %s
        """
        sessions = db.execute_query(sessions_query, (user_id, window_size))

        if not sessions:
            logger.info(f"No sessions to consolidate for user {user_id}")
            return {
                'message': 'No sessions to consolidate', 
                'consolidated_memory_count': 0,
                'session_count': 0
            }

        session_ids = [str(s['session_id']) for s in sessions]
        logger.info(f"Found {len(sessions)} sessions to consolidate: {session_ids}")

        # Retrieve memories from these sessions
        memories_query = """
            SELECT memory_id, text, kind, importance, created_at, session_id
            FROM app.memories
            WHERE session_id = ANY(%s::uuid[])
            AND user_id = %s
            ORDER BY importance DESC, created_at DESC
        """
        memories = db.execute_query(memories_query, (session_ids, user_id))

        if not memories:
            logger.info(f"No memories found in sessions for user {user_id}")
            return {
                'message': 'No memories to consolidate', 
                'consolidated_memory_count': 0,
                'session_count': len(sessions)
            }

        logger.info(f"Found {len(memories)} memories to consolidate")

        # Cluster similar memories
        clusters = self._cluster_memories(memories)
        logger.info(f"Created {len(clusters)} memory clusters")

        # Generate summary for each cluster
        summaries = []
        all_memory_ids = []

        for i, cluster in enumerate(clusters):
            logger.info(f"Processing cluster {i+1}/{len(clusters)} with {len(cluster)} memories")
            
            cluster_text = "\n".join([m['text'] for m in cluster])
            summary_text = self._generate_summary(cluster_text)

            # Generate embedding for summary
            summary_embedding = self.embedding_service.embed_text(summary_text)

            # Calculate importance (max of cluster)
            importance = max(m['importance'] for m in cluster)

            memory_ids = [m['memory_id'] for m in cluster]
            all_memory_ids.extend(memory_ids)

            summaries.append({
                'summary': summary_text,
                'embedding': summary_embedding,
                'memory_ids': memory_ids,
                'importance': importance
            })

        # Store summaries
        summary_ids = self._store_summaries(summaries, user_id, window_size)
        logger.info(f"Stored {len(summary_ids)} summaries")

        # Mark sessions as consolidated
        self._mark_sessions_consolidated(session_ids)
        logger.info(f"Marked {len(session_ids)} sessions as consolidated")

        return {
            'summary_ids': summary_ids,
            'session_window': window_size,
            'consolidated_memory_count': len(all_memory_ids),
            'session_count': len(sessions),
            'summary_count': len(summaries),
            'created_at': datetime.now(timezone.utc).isoformat()
        }

    def _cluster_memories(self, memories: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Cluster similar memories using keyword overlap
        
        Args:
            memories: List of memory dictionaries
            
        Returns:
            List of clusters, each containing similar memories
        """
        clusters = []
        used_indices = set()

        for i, memory in enumerate(memories):
            if i in used_indices:
                continue

            cluster = [memory]
            used_indices.add(i)

            # Extract keywords from memory text
            keywords = set(memory['text'].lower().split())
            
            # Find similar memories based on keyword overlap
            for j, other_memory in enumerate(memories):
                if j in used_indices or i == j:
                    continue

                other_keywords = set(other_memory['text'].lower().split())
                
                # Calculate Jaccard similarity
                intersection = len(keywords & other_keywords)
                union = len(keywords | other_keywords)
                similarity = intersection / union if union > 0 else 0

                # Add to cluster if similarity exceeds threshold
                if similarity > settings.CONSOLIDATION_SIMILARITY_THRESHOLD:
                    cluster.append(other_memory)
                    used_indices.add(j)

            clusters.append(cluster)

        return clusters

    def _generate_summary(self, cluster_text: str) -> str:
        """
        Generate summary using LLM
        
        Args:
            cluster_text: Combined text from memory cluster
            
        Returns:
            Generated summary text
        """
        prompt = f"""Summarize the following conversation memories into a concise, factual statement that captures the key information:

{cluster_text}

Summary:"""

        try:
            response = self.llm_service.generate_response(
                prompt=prompt,
                context=None
            )
            
            summary = response.get('response', '').strip()
            
            # Fallback if summary is too short or empty
            if len(summary) < 10:
                logger.warning("Generated summary too short, using fallback")
                return cluster_text[:200] + "..."
                
            return summary
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return cluster_text[:200] + "..."

    def _store_summaries(self, summaries: List[Dict[str, Any]], user_id: str, window_size: int) -> List[int]:
        """
        Store memory summaries in database
        
        Args:
            summaries: List of summary dictionaries
            user_id: User ID
            window_size: Session window size
            
        Returns:
            List of summary IDs
        """
        if not summaries:
            return []

        query = """
            INSERT INTO app.memory_summaries 
            (user_id, session_window, summary, embedding, consolidated_memory_ids, importance, created_at)
            VALUES %s
            RETURNING summary_id
        """

        values = []
        for summary in summaries:
            values.append((
                user_id,
                window_size,
                summary['summary'],
                summary['embedding'],
                summary['memory_ids'],
                summary['importance'],
                datetime.now(timezone.utc)
            ))

        with db.get_connection() as conn:
            with conn.cursor() as cur:
                from psycopg2.extras import execute_values
                result = execute_values(cur, query, values, fetch=True)
                return [row[0] for row in result]

    def _mark_sessions_consolidated(self, session_ids: List[str]):
        """
        Mark sessions as consolidated
        
        Args:
            session_ids: List of session IDs to mark as consolidated
        """
        if not session_ids:
            return

        query = """
            UPDATE app.sessions
            SET consolidated = true
            WHERE session_id = ANY(%s::uuid[])
        """
        db.execute_update(query, (session_ids,))

    def get_consolidation_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get consolidation statistics for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict with consolidation statistics
        """
        # Count unconsolidated sessions
        unconsolidated_query = """
            SELECT COUNT(*) as count
            FROM app.sessions
            WHERE user_id = %s AND consolidated = false
        """
        unconsolidated_result = db.execute_query(unconsolidated_query, (user_id,), fetch_one=True)
        unconsolidated_count = unconsolidated_result['count'] if unconsolidated_result else 0

        # Count consolidated sessions
        consolidated_query = """
            SELECT COUNT(*) as count
            FROM app.sessions
            WHERE user_id = %s AND consolidated = true
        """
        consolidated_result = db.execute_query(consolidated_query, (user_id,), fetch_one=True)
        consolidated_count = consolidated_result['count'] if consolidated_result else 0

        # Count summaries
        summaries_query = """
            SELECT COUNT(*) as count
            FROM app.memory_summaries
            WHERE user_id = %s
        """
        summaries_result = db.execute_query(summaries_query, (user_id,), fetch_one=True)
        summaries_count = summaries_result['count'] if summaries_result else 0

        return {
            'unconsolidated_sessions': unconsolidated_count,
            'consolidated_sessions': consolidated_count,
            'total_summaries': summaries_count,
            'ready_for_consolidation': unconsolidated_count >= settings.CONSOLIDATION_WINDOW
        }


# Singleton instance
_consolidation_service = None

def get_consolidation_service() -> ConsolidationService:
    """Get singleton consolidation service instance"""
    global _consolidation_service
    if _consolidation_service is None:
        _consolidation_service = ConsolidationService()
    return _consolidation_service
