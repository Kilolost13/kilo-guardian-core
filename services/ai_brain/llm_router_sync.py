"""
LLM Router - Synchronous version using requests
Routes queries to the best model (DeepSeek or Ollama) based on task type
"""

import requests
import os
import logging
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class LLMProvider(Enum):
    DEEPSEEK = "deepseek"
    OLLAMA = "ollama"

class LLMRouter:
    """Smart router that chooses the best LLM for each task"""

    def __init__(self):
        self.deepseek_url = os.getenv("DEEPSEEK_URL", "http://localhost:8080/v1")
        self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
        self.ollama_model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.router_enabled = os.getenv("LLM_ROUTER_ENABLED", "true").lower() == "true"

        logger.info(f"LLM Router initialized: DeepSeek={self.deepseek_url}, Ollama={self.ollama_url}")

    def choose_provider(self, query: str, context: Optional[Dict[str, Any]] = None) -> LLMProvider:
        """Intelligently choose which model to use"""
        if not self.router_enabled:
            return LLMProvider.OLLAMA

        query_lower = query.lower()

        # DeepSeek keywords
        deepseek_keywords = [
            'code', 'function', 'python', 'debug', 'refactor', 'algorithm',
            'prescription', 'ocr', 'extract', 'parse', 'receipt',
            'medication', 'dosage', 'schedule', 'financial', 'categorize'
        ]

        if any(kw in query_lower for kw in deepseek_keywords):
            return LLMProvider.DEEPSEEK

        if context:
            source = context.get('source', '')
            if source in ['meds', 'financial', 'receipt', 'prescription']:
                return LLMProvider.DEEPSEEK

        return LLMProvider.OLLAMA

    def generate(
        self,
        prompt: str,
        provider: Optional[LLMProvider] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text using the specified provider"""
        if provider is None:
            provider = self.choose_provider(prompt)

        logger.info(f"Generating with {provider.value}")

        try:
            if provider == LLMProvider.DEEPSEEK:
                return self._call_deepseek(prompt, max_tokens, temperature, system_prompt)
            else:
                return self._call_ollama(prompt, max_tokens, temperature, system_prompt)
        except Exception as e:
            logger.error(f"Error with {provider.value}: {e}")
            # Fallback
            fallback = LLMProvider.OLLAMA if provider == LLMProvider.DEEPSEEK else LLMProvider.DEEPSEEK
            logger.warning(f"Falling back to {fallback.value}")
            try:
                if fallback == LLMProvider.DEEPSEEK:
                    return self._call_deepseek(prompt, max_tokens, temperature, system_prompt)
                else:
                    return self._call_ollama(prompt, max_tokens, temperature, system_prompt)
            except Exception as e2:
                raise Exception(f"Both providers failed: {e}, {e2}")

    def _call_deepseek(self, prompt: str, max_tokens: int, temperature: float, system_prompt: Optional[str]) -> str:
        """Call DeepSeek via OpenAI-compatible API"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = requests.post(
            f"{self.deepseek_url}/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            return data['choices'][0]['message']['content']
        else:
            raise Exception(f"DeepSeek returned {response.status_code}")

    def _call_ollama(self, prompt: str, max_tokens: int, temperature: float, system_prompt: Optional[str]) -> str:
        """Call Ollama API"""
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"

        response = requests.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": self.ollama_model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            },
            timeout=60
        )

        if response.status_code == 200:
            data = response.json()
            return data['response']
        else:
            raise Exception(f"Ollama returned {response.status_code}")

    def health_check(self) -> Dict[str, bool]:
        """Check health of both providers"""
        status = {"deepseek": False, "ollama": False}

        try:
            r = requests.get(f"{self.deepseek_url.replace('/v1', '')}/health", timeout=5)
            status["deepseek"] = r.status_code == 200
        except:
            pass

        try:
            r = requests.get(f"{self.ollama_url}/api/version", timeout=5)
            status["ollama"] = r.status_code == 200
        except:
            pass

        return status


# Global router instance
llm_router = LLMRouter()
