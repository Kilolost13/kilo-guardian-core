"""
Semantic memory search and retrieval.

This module provides semantic search over the Memory table using embeddings.
Supports privacy-aware filtering and relevance ranking.
"""

import json
import logging
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def search_memories(
    query: str,
    session,
    limit: int = 10,
    privacy_filter: Optional[str] = None,
    source_filter: Optional[str] = None,
    min_similarity: float = 0.3,
    time_window_days: Optional[int] = None
) -> List[Tuple[Any, float]]:
    """
    Search memories using semantic similarity.
    
    Args:
        query: Search query text
        session: SQLAlchemy session
        limit: Maximum number of results
        privacy_filter: Filter by privacy_label ('public', 'private', 'confidential')
        source_filter: Filter by source ('meds', 'finance', 'habits', 'cam', 'user')
        min_similarity: Minimum similarity threshold (0.0 to 1.0)
        time_window_days: Only search memories from last N days (None = all time)
    
    Returns:
        List of (Memory, similarity_score) tuples, sorted by relevance
    """
    from shared.models import Memory
    from .embeddings import embed_text, cosine_similarity
    
    # Generate query embedding
    query_embedding = embed_text(query)
    
    # Build base query
    db_query = session.query(Memory)
    
    # Apply filters
    if privacy_filter:
        db_query = db_query.filter(Memory.privacy_label == privacy_filter)
    
    if source_filter:
        db_query = db_query.filter(Memory.source == source_filter)
    
    if time_window_days:
        cutoff_date = datetime.utcnow() - timedelta(days=time_window_days)
        db_query = db_query.filter(Memory.created_at >= cutoff_date)
    
    # Filter out expired memories (TTL-based)
    # TTL is in seconds from creation
    memories = []
    for mem in db_query.all():
        if mem.ttl_seconds:
            age_seconds = (datetime.utcnow() - mem.created_at).total_seconds()
            if age_seconds > mem.ttl_seconds:
                # Memory expired, skip it
                continue
        memories.append(mem)
    
    # Calculate similarity scores
    results = []
    for memory in memories:
        if memory.embedding_json:
            try:
                mem_embedding = json.loads(memory.embedding_json)
                similarity = cosine_similarity(query_embedding, mem_embedding)
                
                if similarity >= min_similarity:
                    results.append((memory, similarity))
            except Exception as e:
                logger.warning(f"Failed to parse embedding for memory {memory.id}: {e}")
    
    # Sort by similarity (highest first)
    results.sort(key=lambda x: x[1], reverse=True)
    
    # Limit results
    return results[:limit]


def search_memories_by_text(
    query: str,
    session,
    limit: int = 10,
    privacy_filter: Optional[str] = None,
    source_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Search memories and return as dictionaries (API-friendly format).
    
    Returns:
        List of memory dictionaries with similarity scores
    """
    results = search_memories(
        query=query,
        session=session,
        limit=limit,
        privacy_filter=privacy_filter,
        source_filter=source_filter
    )
    
    return [
        {
            "id": mem.id,
            "created_at": mem.created_at.isoformat() if mem.created_at else None,
            "source": mem.source,
            "modality": mem.modality,
            "text": mem.text_blob,
            "metadata": json.loads(mem.metadata_json) if mem.metadata_json else {},
            "privacy_label": mem.privacy_label,
            "similarity": similarity,
            "ttl_seconds": mem.ttl_seconds
        }
        for mem, similarity in results
    ]


def get_relevant_context(
    query: str,
    session,
    max_context_items: int = 5,
    privacy_filter: Optional[str] = None
) -> str:
    """
    Get relevant context for a query as formatted text (for LLM prompts).
    
    Args:
        query: Query text
        session: Database session
        max_context_items: Maximum memories to include
        privacy_filter: Privacy level filter
    
    Returns:
        Formatted context string ready for LLM injection
    """
    results = search_memories(
        query=query,
        session=session,
        limit=max_context_items,
        privacy_filter=privacy_filter,
        min_similarity=0.4  # Higher threshold for context
    )
    
    if not results:
        return ""
    
    context_parts = ["=== Relevant Context from Memory ==="]
    
    for i, (mem, similarity) in enumerate(results, 1):
        context_parts.append(f"\n[Memory {i}] (similarity: {similarity:.2f}, source: {mem.source})")
        context_parts.append(f"  Date: {mem.created_at.strftime('%Y-%m-%d %H:%M') if mem.created_at else 'unknown'}")
        context_parts.append(f"  {mem.text_blob}")
        
        # Include metadata if present
        if mem.metadata_json:
            try:
                metadata = json.loads(mem.metadata_json)
                if metadata:
                    context_parts.append(f"  Metadata: {json.dumps(metadata, indent=2)}")
            except:
                pass
    
    context_parts.append("\n=== End Context ===\n")
    
    return "\n".join(context_parts)


def get_memory_timeline(
    session,
    source: Optional[str] = None,
    limit: int = 50,
    privacy_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get chronological timeline of memories.
    
    Args:
        session: Database session
        source: Filter by source
        limit: Maximum memories to return
        privacy_filter: Filter by privacy label
    
    Returns:
        List of memories in reverse chronological order (newest first)
    """
    from shared.models import Memory
    
    query = session.query(Memory).order_by(Memory.created_at.desc())
    
    if source:
        query = query.filter(Memory.source == source)
    
    if privacy_filter:
        query = query.filter(Memory.privacy_label == privacy_filter)
    
    memories = query.limit(limit).all()
    
    # Filter expired
    results = []
    for mem in memories:
        if mem.ttl_seconds:
            age_seconds = (datetime.utcnow() - mem.created_at).total_seconds()
            if age_seconds > mem.ttl_seconds:
                continue
        
        results.append({
            "id": mem.id,
            "created_at": mem.created_at.isoformat() if mem.created_at else None,
            "source": mem.source,
            "modality": mem.modality,
            "text": mem.text_blob,
            "metadata": json.loads(mem.metadata_json) if mem.metadata_json else {},
            "privacy_label": mem.privacy_label,
            "ttl_seconds": mem.ttl_seconds
        })
    
    return results


def delete_memory(memory_id: int, session) -> bool:
    """
    Delete a memory by ID.
    
    Args:
        memory_id: Memory ID to delete
        session: Database session
    
    Returns:
        True if deleted, False if not found
    """
    from shared.models import Memory
    
    memory = session.query(Memory).filter(Memory.id == memory_id).first()
    if memory:
        session.delete(memory)
        session.commit()
        logger.info(f"Deleted memory {memory_id}")
        return True
    
    logger.warning(f"Memory {memory_id} not found")
    return False


def update_memory_privacy(memory_id: int, privacy_label: str, session) -> bool:
    """
    Update privacy label for a memory.
    
    Args:
        memory_id: Memory ID
        privacy_label: New privacy label ('public', 'private', 'confidential')
        session: Database session
    
    Returns:
        True if updated, False if not found
    """
    from shared.models import Memory
    
    valid_labels = ['public', 'private', 'confidential']
    if privacy_label not in valid_labels:
        raise ValueError(f"Invalid privacy_label. Must be one of: {valid_labels}")
    
    memory = session.query(Memory).filter(Memory.id == memory_id).first()
    if memory:
        memory.privacy_label = privacy_label
        session.commit()
        logger.info(f"Updated memory {memory_id} privacy to {privacy_label}")
        return True
    
    return False


if __name__ == "__main__":
    # Test module
    logging.basicConfig(level=logging.INFO)
    print("Memory search module loaded successfully")
