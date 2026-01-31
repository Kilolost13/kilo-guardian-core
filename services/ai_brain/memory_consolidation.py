"""
Memory consolidation service for long-term storage optimization.

Periodically summarizes old memories to reduce storage and improve retrieval.
Respects TTL settings and privacy labels.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


def consolidate_old_memories(
    session,
    days_old: int = 30,
    batch_size: int = 100,
    dry_run: bool = False
) -> dict:
    """
    Consolidate memories older than specified days into summaries.
    
    Args:
        session: Database session
        days_old: Consolidate memories older than this many days
        batch_size: Maximum memories to process in one run
        dry_run: If True, don't actually delete/modify memories
    
    Returns:
        Dictionary with consolidation statistics
    """
    from shared.models import Memory
    from .embeddings import embed_text
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    
    # Get old memories, grouped by source
    old_memories = session.query(Memory).filter(
        Memory.created_at < cutoff_date,
        Memory.source != "conversation"  # Don't consolidate conversations
    ).limit(batch_size).all()
    
    if not old_memories:
        logger.info("No old memories to consolidate")
        return {"consolidated": 0, "deleted": 0}
    
    # Group by source
    by_source = defaultdict(list)
    for mem in old_memories:
        by_source[mem.source].append(mem)
    
    stats = {
        "consolidated": 0,
        "deleted": 0,
        "summaries_created": 0,
        "by_source": {}
    }
    
    # Create summary for each source
    for source, memories in by_source.items():
        logger.info(f"Consolidating {len(memories)} memories from source: {source}")
        
        # Create summary text
        summary_parts = [
            f"Memory consolidation summary for {source}",
            f"Period: {memories[-1].created_at.date()} to {memories[0].created_at.date()}",
            f"Total events: {len(memories)}",
            "",
            "Events:"
        ]
        
        # Sample up to 10 representative memories
        sample_size = min(10, len(memories))
        step = len(memories) // sample_size if sample_size > 0 else 1
        sampled = memories[::step][:sample_size]
        
        for mem in sampled:
            summary_parts.append(f"  - {mem.text_blob[:100]}")
        
        if len(memories) > sample_size:
            summary_parts.append(f"  ... and {len(memories) - sample_size} more events")
        
        summary_text = "\n".join(summary_parts)
        
        if not dry_run:
            # Create summary memory
            summary_embedding = embed_text(summary_text)
            summary_mem = Memory(
                source=f"{source}_summary",
                modality="text",
                text_blob=summary_text,
                metadata_json=json.dumps({
                    "consolidated_count": len(memories),
                    "date_range": {
                        "start": memories[-1].created_at.isoformat(),
                        "end": memories[0].created_at.isoformat()
                    }
                }),
                embedding_json=json.dumps(summary_embedding),
                privacy_label="private"
            )
            session.add(summary_mem)
            
            # Delete original memories
            for mem in memories:
                session.delete(mem)
            
            session.commit()
            stats["summaries_created"] += 1
            stats["deleted"] += len(memories)
        
        stats["by_source"][source] = len(memories)
        stats["consolidated"] += len(memories)
    
    logger.info(f"Consolidation complete: {stats}")
    return stats


def cleanup_expired_memories(session, dry_run: bool = False) -> int:
    """
    Delete memories that have exceeded their TTL.
    
    Args:
        session: Database session
        dry_run: If True, don't actually delete
    
    Returns:
        Number of expired memories deleted
    """
    from shared.models import Memory
    
    all_memories = session.query(Memory).filter(Memory.ttl_seconds.isnot(None)).all()
    
    expired = []
    now = datetime.utcnow()
    
    for mem in all_memories:
        if mem.ttl_seconds:
            age_seconds = (now - mem.created_at).total_seconds()
            if age_seconds > mem.ttl_seconds:
                expired.append(mem)
    
    if not expired:
        logger.info("No expired memories found")
        return 0
    
    logger.info(f"Found {len(expired)} expired memories")
    
    if not dry_run:
        for mem in expired:
            logger.debug(f"Deleting expired memory {mem.id} (age: {age_seconds}s, TTL: {mem.ttl_seconds}s)")
            session.delete(mem)
        session.commit()
    
    return len(expired)


def optimize_embeddings(session, dry_run: bool = False) -> int:
    """
    Regenerate embeddings for memories that have old hash-based embeddings.
    
    Args:
        session: Database session
        dry_run: If True, don't actually update
    
    Returns:
        Number of embeddings updated
    """
    from shared.models import Memory
    from .embeddings import embed_text, get_embedding_model
    
    # Check if we have a real embedding model
    model = get_embedding_model()
    if model is None:
        logger.warning("No embedding model available - skipping optimization")
        return 0
    
    # Find memories with small embeddings (likely hash-based, dimension 8)
    memories = session.query(Memory).filter(Memory.embedding_json.isnot(None)).all()
    
    updated = 0
    for mem in memories:
        if mem.embedding_json:
            try:
                emb = json.loads(mem.embedding_json)
                if len(emb) < 100:  # Likely old hash-based embedding (dim 8)
                    if not dry_run:
                        # Regenerate with proper model
                        new_emb = embed_text(mem.text_blob)
                        mem.embedding_json = json.dumps(new_emb)
                        updated += 1
                    else:
                        updated += 1
            except:
                pass
    
    if not dry_run and updated > 0:
        session.commit()
    
    logger.info(f"Optimized {updated} embeddings")
    return updated


def run_nightly_maintenance(session):
    """
    Run all maintenance tasks.
    
    This should be called periodically (e.g., via cron or scheduler).
    """
    logger.info("=" * 60)
    logger.info("Starting nightly memory maintenance")
    logger.info("=" * 60)
    
    # 1. Cleanup expired memories
    logger.info("Step 1: Cleaning up expired memories...")
    expired_count = cleanup_expired_memories(session, dry_run=False)
    logger.info(f"  → Deleted {expired_count} expired memories")
    
    # 2. Consolidate old memories (older than 30 days)
    logger.info("Step 2: Consolidating old memories...")
    consolidation_stats = consolidate_old_memories(session, days_old=30, dry_run=False)
    logger.info(f"  → Consolidated {consolidation_stats['consolidated']} memories")
    logger.info(f"  → Created {consolidation_stats['summaries_created']} summaries")
    
    # 3. Optimize embeddings
    logger.info("Step 3: Optimizing embeddings...")
    optimized_count = optimize_embeddings(session, dry_run=False)
    logger.info(f"  → Updated {optimized_count} embeddings")
    
    logger.info("=" * 60)
    logger.info("Nightly maintenance complete")
    logger.info("=" * 60)
    
    return {
        "expired_deleted": expired_count,
        "consolidated": consolidation_stats['consolidated'],
        "embeddings_optimized": optimized_count
    }


if __name__ == "__main__":
    # Test module
    logging.basicConfig(level=logging.INFO)
    print("Memory consolidation module loaded successfully")
