"""
Embedding generation for semantic memory search.

This module provides local embedding generation using sentence-transformers.
All models run locally - no external API calls required for air-gapped deployment.
"""

import os
import json
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Global model cache to avoid reloading
_embedding_model = None


def get_embedding_model():
    """
    Load and cache the sentence-transformers model for embedding generation.
    
    Uses all-MiniLM-L6-v2 by default (lightweight, fast, good quality).
    Falls back to simple hash-based embeddings if model unavailable.
    
    Returns:
        SentenceTransformer model or None if unavailable
    """
    global _embedding_model
    
    if _embedding_model is not None:
        return _embedding_model
    
    try:
        from sentence_transformers import SentenceTransformer
        
        # Check for local model path first (air-gapped deployment)
        model_name = os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        model_path = os.environ.get("EMBEDDING_MODEL_PATH")
        
        if model_path and os.path.exists(model_path):
            logger.info(f"Loading embedding model from local path: {model_path}")
            _embedding_model = SentenceTransformer(model_path)
        else:
            # Try to load from cache or download (requires network)
            logger.info(f"Loading embedding model: {model_name}")
            cache_folder = os.environ.get("SENTENCE_TRANSFORMERS_HOME", "./models/sentence_transformers")
            _embedding_model = SentenceTransformer(model_name, cache_folder=cache_folder)
        
        logger.info("Embedding model loaded successfully")
        return _embedding_model
        
    except ImportError:
        logger.warning("sentence-transformers not installed. Install: pip install sentence-transformers")
        return None
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        return None


def embed_text(text: str, model=None) -> List[float]:
    """
    Generate embedding vector for text.
    
    Args:
        text: Input text to embed
        model: Optional pre-loaded model (if None, will load default)
    
    Returns:
        List of floats representing the embedding vector (384 dimensions for all-MiniLM-L6-v2)
        Falls back to simple hash-based embedding if model unavailable
    """
    if not text:
        # Return zero vector for empty text
        return [0.0] * 384
    
    if model is None:
        model = get_embedding_model()
    
    if model is not None:
        try:
            # Generate embedding using sentence-transformers
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
    
    # Fallback: simple hash-based embedding (not semantic, but deterministic)
    logger.warning("Using fallback hash-based embedding (not semantic)")
    return _hash_based_embedding(text)


def embed_batch(texts: List[str], model=None) -> List[List[float]]:
    """
    Generate embeddings for multiple texts (more efficient than one-by-one).
    
    Args:
        texts: List of input texts
        model: Optional pre-loaded model
    
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    if model is None:
        model = get_embedding_model()
    
    if model is not None:
        try:
            embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=len(texts) > 10)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {e}")
    
    # Fallback
    logger.warning(f"Using fallback hash-based embeddings for {len(texts)} texts")
    return [_hash_based_embedding(text) for text in texts]


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Args:
        vec1, vec2: Embedding vectors
    
    Returns:
        Similarity score between -1 and 1 (higher = more similar)
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    
    # Dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    # Magnitudes
    mag1 = sum(a * a for a in vec1) ** 0.5
    mag2 = sum(b * b for b in vec2) ** 0.5
    
    if mag1 == 0 or mag2 == 0:
        return 0.0
    
    return dot_product / (mag1 * mag2)


def _hash_based_embedding(text: str, dim: int = 384) -> List[float]:
    """
    Fallback embedding using deterministic hashing.
    NOT semantic - only useful for exact/near-exact matches.
    
    Args:
        text: Input text
        dim: Embedding dimension (default 384 to match all-MiniLM-L6-v2)
    
    Returns:
        Pseudo-embedding vector
    """
    import hashlib
    
    # Normalize text
    text = text.lower().strip()
    
    # Generate multiple hashes to fill dimension
    embedding = []
    for i in range(0, dim, 32):  # SHA256 produces 32 bytes
        hash_input = f"{text}:{i}".encode()
        hash_bytes = hashlib.sha256(hash_input).digest()
        
        # Convert bytes to floats in range [-1, 1]
        for byte in hash_bytes:
            if len(embedding) >= dim:
                break
            # Map byte (0-255) to float (-1 to 1)
            embedding.append((byte / 127.5) - 1.0)
    
    # Normalize to unit vector
    magnitude = sum(x * x for x in embedding) ** 0.5
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]
    
    return embedding[:dim]


# Convenience function for backward compatibility
def _embed_text(text: str) -> List[float]:
    """Legacy function name - redirects to embed_text"""
    return embed_text(text)


if __name__ == "__main__":
    # Test the embedding functions
    logging.basicConfig(level=logging.INFO)
    
    print("Testing embedding generation...")
    
    # Test single embedding
    text1 = "I took my medication this morning"
    text2 = "I remembered to take my pills today"
    text3 = "I bought groceries at the store"
    
    emb1 = embed_text(text1)
    emb2 = embed_text(text2)
    emb3 = embed_text(text3)
    
    print(f"\nEmbedding dimension: {len(emb1)}")
    
    # Test similarity
    sim_12 = cosine_similarity(emb1, emb2)
    sim_13 = cosine_similarity(emb1, emb3)
    sim_23 = cosine_similarity(emb2, emb3)
    
    print(f"\nSimilarity scores:")
    print(f"  '{text1}' <-> '{text2}': {sim_12:.3f}")
    print(f"  '{text1}' <-> '{text3}': {sim_13:.3f}")
    print(f"  '{text2}' <-> '{text3}': {sim_23:.3f}")
    
    # Test batch
    texts = [text1, text2, text3]
    batch_embs = embed_batch(texts)
    print(f"\nBatch embedding: generated {len(batch_embs)} embeddings")
