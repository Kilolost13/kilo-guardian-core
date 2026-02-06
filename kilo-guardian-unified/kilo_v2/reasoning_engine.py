import logging
import os
import httpx
import asyncio
import numpy as np

from kilo_v2.local_llm import LocalLlm
from kilo_v2.security_utils import sanitize_prompt_for_llm
from kilo_v2.user_context import UserContext

# Disable tokenizers parallelism to prevent fork warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

logger = logging.getLogger("ReasoningEngine")

# --- GLOBAL MODEL INITIALIZATION ---
AI_BRAIN_URL = os.getenv("AI_BRAIN_URL", "http://kilo-ai-brain:9004")

# 1. Sentence Transformer for routing
try:
    from sentence_transformers import SentenceTransformer
    try:
        embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("✅ Loaded SentenceTransformer model: all-MiniLM-L6-v2")
    except Exception as e:
        embedding_model = None
        logger.warning(f"⚠️ Failed to load SentenceTransformer model: {e}. Routing will be keyword-based.")
except ImportError:
    embedding_model = None
    logger.warning("⚠️ sentence-transformers not installed. Routing will be keyword-based.")

# 2. Local Generative LLM for conversational fallback
local_llm = None
try:
    from kilo_v2 import config
    if config.LOCAL_LLM_MODEL_PATH and os.path.exists(config.LOCAL_LLM_MODEL_PATH):
        local_llm = LocalLlm(model_path=config.LOCAL_LLM_MODEL_PATH)
        logger.info("✅ Initialized Local LLM for conversational responses.")
except Exception as e:
    logger.error(f"❌ Failed to initialize Local LLM: {e}")


# --- IN-MEMORY CACHE ---
embedding_cache = {}
plugin_keyword_embeddings = {}

def get_embedding(text):
    if not embedding_model: return np.zeros(384)
    if text in embedding_cache: return embedding_cache[text]
    embedding = embedding_model.encode([text], show_progress_bar=False)[0]
    embedding_cache[text] = embedding
    return embedding

def precompute_plugin_embeddings(plugin_manager):
    if not embedding_model: return
    plugin_keyword_embeddings.clear()
    for plugin in plugin_manager.plugins:
        name = plugin.get_name()
        keywords = plugin.get_keywords()
        if keywords:
            try:
                embeddings = embedding_model.encode(keywords, show_progress_bar=False)
                plugin_keyword_embeddings[name] = {"keywords": keywords, "embeddings": embeddings}
            except Exception: pass

async def call_ai_brain(query: str):
    """Delegate deep reasoning to the AI Brain microservice."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{AI_BRAIN_URL}/chat", json={"message": query})
            if resp.status_code == 200:
                return resp.json().get("response")
    except Exception as e:
        logger.error(f"AI Brain call failed: {e}")
    return None

def synthesize_answer(query, plugin_manager, user_context: UserContext = None):
    # Try routing to plugin first
    if embedding_model:
        query_embedding = get_embedding(query)
        best_plugin, highest_similarity = None, -1.0

        for plugin in plugin_manager.plugins:
            if not getattr(plugin, "enabled", True): continue
            name = plugin.get_name()
            if name in plugin_keyword_embeddings:
                for kw_emb in plugin_keyword_embeddings[name]["embeddings"]:
                    sim = np.dot(query_embedding, kw_emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(kw_emb))
                    if sim > highest_similarity:
                        highest_similarity = sim
                        best_plugin = plugin

        if best_plugin and highest_similarity > 0.65:
            logger.info(f"Routing to plugin '{best_plugin.get_name()}'")
            try:
                if hasattr(best_plugin, "execute") and callable(best_plugin.execute):
                    return best_plugin.execute(query)
                else:
                    return best_plugin.run(query)
            except Exception as e:
                logger.error(f"Plugin error: {e}")

    # NO CONFIDENT PLUGIN -> DELEGATE TO AI BRAIN (RAG/Deep Intelligence)
    logger.info("Delegating query to AI Brain...")
    try:
        # Run async call in sync context for Guardian compatibility
        loop = asyncio.get_event_loop()
        brain_response = loop.run_until_complete(call_ai_brain(query))
        if brain_response:
            return {"type": "chat_response", "content": brain_response, "source": "ai-brain"}
    except Exception as e:
        logger.error(f"Brain delegation failed: {e}")

    # Fallback to Local LLM if brain fails
    if local_llm:
        response = local_llm.call(f"User: {query}\nAnswer:")
        return {"type": "chat_response", "content": response, "source": "local-llm"}

    return {"type": "chat_response", "content": "I'm having trouble connecting to my deep reasoning centers."}