"""
Retrieval Augmented Generation (RAG) for context-aware AI responses.

This module implements RAG to inject relevant memories into LLM prompts,
enabling the AI to provide context-aware responses based on past interactions.
"""

import os
import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


def generate_rag_response(
    user_query: str,
    session,
    max_context_memories: int = 5,
    llm_provider: Optional[str] = None,
    model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a response using RAG: retrieve relevant memories and augment LLM prompt.
    
    Args:
        user_query: User's question/input
        session: Database session for memory retrieval
        max_context_memories: Maximum memories to inject into context
        llm_provider: LLM provider ('ollama', 'library', or None for auto)
        model: Model name (e.g., 'tinyllama', 'mistral')
    
    Returns:
        Dictionary with 'response', 'context_used', and 'sources'
    """
    from .memory_search import search_memories
    from .embeddings import embed_text
    
    # Step 1: Retrieve relevant memories
    logger.info(f"Searching for relevant memories for query: '{user_query}'")
    memory_results = search_memories(
        query=user_query,
        session=session,
        limit=max_context_memories,
        min_similarity=0.3,
        privacy_filter=None  # Include all privacy levels (can be customized)
    )
    
    # Step 2: Format context
    context_parts = []
    sources = []
    
    if memory_results:
        context_parts.append("=== Your Memory Context ===")
        for i, (mem, similarity) in enumerate(memory_results, 1):
            context_parts.append(
                f"[Memory {i}] ({mem.source}, {mem.created_at.strftime('%Y-%m-%d')}): {mem.text_blob}"
            )
            sources.append({
                "id": mem.id,
                "source": mem.source,
                "similarity": similarity,
                "text": mem.text_blob[:100] + "..." if len(mem.text_blob) > 100 else mem.text_blob
            })
        context_parts.append("=== End Context ===\n")
    
    context_str = "\n".join(context_parts)
    
    # Step 3: Build augmented prompt with Kilo personality
    system_prompt = """You are Kilo, Kyle's personal AI assistant. You help Kyle track his health, habits, finances, and daily life.

Your personality:
- Friendly, supportive, and slightly witty
- Proactive in helping Kyle stay on track with his habits
- You remember Kyle's preferences and patterns
- You provide actionable advice, not generic tips
- You are concise and direct, respecting Kyle's time

Your capabilities:
- Track medications and health data
- Monitor habits and provide encouragement
- Manage finances and budgets
- Remember important information about Kyle's life
- Learn from patterns to give better recommendations over time
"""

    augmented_prompt = f"""{system_prompt}

{context_str}

Kyle's Question: {user_query}

Instructions: Answer Kyle's question using the memory context provided above when relevant.
If the memories contain relevant information, reference them naturally in your answer.
Be conversational, supportive, and concise. Remember you're Kilo, Kyle's AI assistant.

Kilo's Response:"""
    
    # Step 4: Generate response using LLM
    if llm_provider is None:
        llm_provider = os.environ.get("LLM_PROVIDER", "ollama")
    
    response_text = ""
    
    if llm_provider == "ollama":
        try:
            from .circuit_breaker import breaker, CircuitBreakerException
            # Check breaker before making the expensive call
            breaker.check_and_reset(augmented_prompt)
            response_text = _generate_ollama_response(augmented_prompt, model)
        except CircuitBreakerException as e:
            logger.warning(f"Request blocked by circuit breaker: {e}")
            return {
                "response": str(e),
                "context_used": 0,
                "sources": [],
                "augmented_prompt": None
            }
    elif llm_provider == "library":
        # Fallback: search library of truth instead
        response_text = _generate_library_response(user_query)
    else:
        response_text = f"I found {len(memory_results)} relevant memories, but no LLM is configured. Please set LLM_PROVIDER environment variable."
    
    return {
        "response": response_text,
        "context_used": len(memory_results),
        "sources": sources,
        "augmented_prompt": augmented_prompt if os.environ.get("DEBUG") else None
    }


def _generate_ollama_response(prompt: str, model: Optional[str] = None) -> str:
    """
    Generate response using Ollama HTTP API or OpenAI-compatible API (llama.cpp server).
    
    Args:
        prompt: Full prompt with context
        model: Model name
    
    Returns:
        Generated response text
    """
    import httpx
    
    ollama_url = os.environ.get("OLLAMA_URL", "http://ollama:11434")
    if model is None:
        model = os.environ.get("OLLAMA_MODEL", "tinyllama")
    
    try:
        logger.info(f"Calling LLM API at {ollama_url} with model: {model}")
        
        # Try OpenAI-compatible endpoint first (llama.cpp server)
        openai_payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.7
        }
        
        response = httpx.post(
            f"{ollama_url}/v1/chat/completions",
            json=openai_payload,
            timeout=180
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            if response_text:
                logger.info("OpenAI-compatible response generated successfully")
                return response_text
        
        # Fallback to Ollama native API
        logger.info("OpenAI endpoint failed, trying Ollama native API")
        ollama_payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        response = httpx.post(
            f"{ollama_url}/api/generate",
            json=ollama_payload,
            timeout=180
        )
        
        if response.status_code == 200:
            result = response.json()
            response_text = result.get("response", "").strip()
            logger.info("Ollama native response generated successfully")
            return response_text
        else:
            error_msg = response.text
            logger.error(f"LLM API error: {response.status_code} - {error_msg}")
            return f"(LLM API error: {response.status_code})"
            
    except httpx.TimeoutException:
        logger.error("LLM request timed out")
        return "(Response generation timed out. Try a faster model.)"
    except Exception as e:
        logger.error(f"LLM API call failed: {e}")
        return f"(Error generating response: {e})"


def _generate_library_response(query: str) -> str:
    """
    Fallback: generate response using Library of Truth search.

    Args:
        query: User query

    Returns:
        Synthesized response from library
    """
    import httpx

    LIBRARY_URL = os.environ.get("LIBRARY_URL", "http://library_of_truth:9006")

    try:
        # Synchronous call (could be made async)
        response = httpx.get(f"{LIBRARY_URL}/search", params={"q": query, "limit": 3}, timeout=5)
        if response.status_code == 200:
            passages = response.json()
            if passages:
                summary = [f"From {p['book']} (p.{p['page']}): {p['text']}" for p in passages]
                return f"Based on the Library of Truth:\n" + "\n".join(summary)
    except Exception as e:
        logger.error(f"Library search failed: {e}")

    # Friendly conversational fallback for air-gapped mode - Kilo personality
    return f"Hey Kyle! I'm Kilo, your AI assistant. I searched my memories but didn't find specific information about '{query}'. You can:\n• Use /remember to store new information\n• Use /recall to search your memories\n• Ask me about your medications, habits, or finances\n• Upload images for prescription or receipt scanning\n\nWhat can I help you with today?"


def store_conversation_memory(
    user_query: str,
    ai_response: str,
    session,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Store a conversation turn as a memory for future retrieval.
    
    Args:
        user_query: What the user asked
        ai_response: What the AI responded
        session: Database session
        metadata: Optional additional metadata
    
    Returns:
        Memory ID
    """
    from shared.models import Memory
    from .embeddings import embed_text
    
    # Create text blob combining query and response
    text_blob = f"User asked: {user_query}\nAssistant responded: {ai_response}"
    
    # Generate embedding
    embedding = embed_text(text_blob)
    
    # Prepare metadata
    if metadata is None:
        metadata = {}
    metadata.update({
        "user_query": user_query,
        "ai_response": ai_response,
        "conversation_turn": True
    })
    
    # Create memory
    memory = Memory(
        source="conversation",
        modality="text",
        text_blob=text_blob,
        metadata_json=json.dumps(metadata),
        embedding_json=json.dumps(embedding),
        privacy_label="private"  # Conversations are private by default
    )
    
    session.add(memory)
    session.commit()
    session.refresh(memory)
    
    logger.info(f"Stored conversation memory: {memory.id}")
    return memory.id


if __name__ == "__main__":
    # Test RAG module
    logging.basicConfig(level=logging.INFO)
    print("RAG module loaded successfully")
