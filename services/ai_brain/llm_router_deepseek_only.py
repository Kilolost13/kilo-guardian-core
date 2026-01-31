"""
LLM Router - DeepSeek Only (No Ollama)
Simplified router that only uses DeepSeek Coder V2 via llama.cpp
"""

import requests
import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class LLMRouter:
    """Router configured for DeepSeek only (no Ollama)"""

    def __init__(self):
        self.deepseek_url = os.getenv("DEEPSEEK_URL", "http://localhost:8080/v1")
        logger.info(f"LLM Router initialized (DeepSeek only): {self.deepseek_url}")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate text using DeepSeek

        Args:
            prompt: The user prompt/question
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system_prompt: Optional system prompt for context

        Returns:
            Generated text response
        """
        logger.info(f"Generating with DeepSeek (max_tokens={max_tokens}, temp={temperature})")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = requests.post(
                f"{self.deepseek_url}/chat/completions",
                json={
                    "model": "gpt-3.5-turbo",  # Placeholder name
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
                error_msg = f"DeepSeek API returned {response.status_code}: {response.text[:200]}"
                logger.error(error_msg)
                raise Exception(error_msg)

        except requests.exceptions.ConnectionError as e:
            error_msg = f"Cannot connect to DeepSeek at {self.deepseek_url}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except requests.exceptions.Timeout:
            error_msg = "DeepSeek request timed out (60s)"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            raise

    def health_check(self) -> Dict[str, Any]:
        """
        Check health of DeepSeek server

        Returns:
            Dict with status and info
        """
        try:
            response = requests.get(
                f"{self.deepseek_url.replace('/v1', '')}/health",
                timeout=5
            )

            return {
                "status": "online" if response.status_code == 200 else "error",
                "url": self.deepseek_url,
                "model": "DeepSeek Coder V2 Lite"
            }
        except Exception as e:
            return {
                "status": "offline",
                "url": self.deepseek_url,
                "error": str(e)
            }


# Global router instance
llm_router = LLMRouter()
