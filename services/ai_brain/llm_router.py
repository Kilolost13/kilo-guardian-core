"""
LLM Router - Intelligent model selection for Kilo Guardian
Routes queries to the best model (DeepSeek or Ollama) based on task type

DeepSeek (localhost:8080): Code, technical analysis, structured data extraction
Ollama (localhost:11434): General chat, quick responses, casual queries
"""

import httpx
import os
import logging
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    DEEPSEEK = "deepseek"  # localhost:8080 - Better for coding/analysis
    OLLAMA = "ollama"      # localhost:11434 - Better for chat

class LLMRouter:
    """Smart router that chooses the best LLM for each task"""

    def __init__(self):
        self.deepseek_url = os.getenv("DEEPSEEK_URL", "http://localhost:8080/v1")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

        # Router enabled flag (can disable DeepSeek if needed)
        self.router_enabled = os.getenv("LLM_ROUTER_ENABLED", "true").lower() == "true"

        logger.info(f"LLM Router initialized: DeepSeek={self.deepseek_url}, Ollama={self.ollama_url}")

    def choose_provider(self, query: str, context: Optional[Dict[str, Any]] = None) -> LLMProvider:
        """
        Intelligently choose which model to use based on query type

        Args:
            query: The user's question or prompt
            context: Optional context dict with 'source', 'task_type', etc.

        Returns:
            LLMProvider enum (DEEPSEEK or OLLAMA)
        """
        if not self.router_enabled:
            return LLMProvider.OLLAMA  # Default when router disabled

        query_lower = query.lower()

        # DeepSeek is better for technical tasks
        deepseek_keywords = [
            # Coding
            'code', 'function', 'python', 'javascript', 'debug',
            'refactor', 'algorithm', 'class', 'api', 'sql',
            'bug', 'error', 'fix', 'implement', 'script',

            # Data extraction
            'prescription', 'ocr', 'analyze image', 'extract data',
            'structured data', 'json', 'parse', 'receipt',
            'medication', 'dosage', 'schedule',

            # Technical analysis
            'analyze', 'categorize', 'summarize document',
            'technical', 'documentation', 'explain code',
            'review', 'optimize', 'performance',

            # Medical/Financial (needs accuracy)
            'medicine', 'drug', 'doctor', 'prescriber',
            'budget', 'expense', 'transaction', 'financial'
        ]

        # Check if query contains technical keywords
        if any(kw in query_lower for kw in deepseek_keywords):
            logger.info(f"Routing to DeepSeek (technical query detected)")
            return LLMProvider.DEEPSEEK

        # Check context clues
        if context:
            source = context.get('source', '')
            task_type = context.get('task_type', '')

            # Route these sources to DeepSeek for better accuracy
            if source in ['meds', 'financial', 'receipt', 'prescription', 'library']:
                logger.info(f"Routing to DeepSeek (source={source})")
                return LLMProvider.DEEPSEEK

            # Specific task types
            if task_type in ['code_generation', 'data_extraction', 'technical_analysis']:
                logger.info(f"Routing to DeepSeek (task_type={task_type})")
                return LLMProvider.DEEPSEEK

        # Default to Ollama for general chat (faster, lighter)
        logger.info("Routing to Ollama (general query)")
        return LLMProvider.OLLAMA

    async def generate(
        self,
        prompt: str,
        provider: Optional[LLMProvider] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text using the specified provider

        Args:
            prompt: The user prompt/question
            provider: Which LLM to use (auto-selected if None)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system_prompt: Optional system prompt for context

        Returns:
            Generated text response
        """
        # Auto-select provider if not specified
        if provider is None:
            provider = self.choose_provider(prompt)

        logger.info(f"Generating with {provider.value} (max_tokens={max_tokens}, temp={temperature})")

        try:
            if provider == LLMProvider.DEEPSEEK:
                return await self._call_deepseek(prompt, max_tokens, temperature, system_prompt)
            else:
                return await self._call_ollama(prompt, max_tokens, temperature, system_prompt)
        except Exception as e:
            logger.error(f"Error with {provider.value}: {e}")

            # Auto-fallback to the other provider
            fallback = LLMProvider.OLLAMA if provider == LLMProvider.DEEPSEEK else LLMProvider.DEEPSEEK
            logger.warning(f"Falling back to {fallback.value}")

            try:
                if fallback == LLMProvider.DEEPSEEK:
                    return await self._call_deepseek(prompt, max_tokens, temperature, system_prompt)
                else:
                    return await self._call_ollama(prompt, max_tokens, temperature, system_prompt)
            except Exception as e2:
                logger.error(f"Fallback also failed: {e2}")
                raise Exception(f"Both LLM providers failed: {e}, {e2}")

    async def _call_deepseek(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str]
    ) -> str:
        """Call DeepSeek via OpenAI-compatible API"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.deepseek_url}/chat/completions",
                    json={
                        "model": "gpt-3.5-turbo",  # Placeholder (llama-server accepts any)
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data['choices'][0]['message']['content']
                else:
                    raise Exception(f"DeepSeek API returned {response.status_code}: {response.text}")

            except httpx.TimeoutException:
                raise Exception("DeepSeek request timed out (60s)")
            except httpx.ConnectError:
                raise Exception(f"Cannot connect to DeepSeek at {self.deepseek_url}")

    async def _call_ollama(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str]
    ) -> str:
        """Call Ollama API"""
        try:
            from .circuit_breaker import breaker
            # Check breaker - using full prompt estimation
            full_text = prompt + (system_prompt if system_prompt else "")
            breaker.check_and_reset(full_text)
        except Exception as e:
            # Re-raise as a standard Exception so it can be caught/logged upstream
            raise Exception(str(e))

        # Combine system prompt with user prompt for Ollama
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.ollama_model,
                        "prompt": full_prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens
                        }
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    return data['response']
                else:
                    raise Exception(f"Ollama API returned {response.status_code}: {response.text}")

            except httpx.TimeoutException:
                raise Exception("Ollama request timed out (60s)")
            except httpx.ConnectError:
                raise Exception(f"Cannot connect to Ollama at {self.ollama_url}")

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of both LLM providers

        Returns:
            Dict with status of each provider
        """
        status = {
            "deepseek": False,
            "ollama": False
        }

        # Check DeepSeek
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.deepseek_url.replace('/v1', '')}/health")
                status["deepseek"] = response.status_code == 200
        except:
            pass

        # Check Ollama
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/version")
                status["ollama"] = response.status_code == 200
        except:
            pass

        logger.info(f"Health check: {status}")
        return status


# Global router instance (singleton)
llm_router = LLMRouter()
