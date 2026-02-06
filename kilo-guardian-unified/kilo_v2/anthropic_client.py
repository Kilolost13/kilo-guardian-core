# kilo_v2/anthropic_client.py
"""
Anthropic Claude API client for Kilo Guardian.

This module provides a lightweight wrapper around the Anthropic API for
conversational AI responses when plugins don't match a query. It uses
Claude 3.5 Haiku for cost-effectiveness while maintaining quality responses
for TBI memory assistance.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger("AnthropicClient")

try:
    from anthropic import Anthropic, APIConnectionError, APIError, RateLimitError

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("⚠️ anthropic package not installed. API integration unavailable.")


class AnthropicClient:
    """
    Client for making API calls to Anthropic's Claude models.

    Designed as a drop-in replacement for LocalLlm with similar interface.
    Optimized for TBI memory assistance use case with brief, helpful responses.
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern to reuse client instance."""
        if cls._instance is None:
            cls._instance = super(AnthropicClient, cls).__new__(cls)
        return cls._instance

    def __init__(
        self, api_key: Optional[str] = None, model: str = "claude-3-5-haiku-20241022"
    ):
        """
        Initialize the Anthropic client.

        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            model: Claude model to use. Defaults to Haiku for cost-effectiveness.
        """
        if hasattr(self, "_initialized") and self._initialized:
            return

        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError(
                "anthropic package not installed. Run: pip install anthropic>=0.40.0"
            )

        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not provided. Set it in .env or pass to constructor."
            )

        self.model = model
        self.client = Anthropic(api_key=self.api_key)
        self._initialized = True

        logger.info(f"✅ AnthropicClient initialized with model: {self.model}")

    @property
    def system_prompt(self) -> str:
        """
        System prompt that defines Kilo Guardian's personality and purpose.

        Emphasizes:
        - TBI/memory assistance focus
        - Brief, clear responses
        - Helpful and encouraging tone
        - Plugin routing hints for common tasks
        """
        return """You are Kilo Guardian, a compassionate AI memory assistant designed specifically for individuals with Traumatic Brain Injury (TBI) and memory challenges.

Your Purpose:
- Help users remember medications, appointments, and daily tasks
- Provide gentle reminders and encouragement
- Keep responses BRIEF and CLEAR (1-3 sentences when possible)
- Use simple language without medical jargon

Core Capabilities (via plugins):
- REMINDERS: Setting time-based alerts ("remind me to...", "set reminder...")
- MEDICATIONS: Tracking med schedules ("when did I take...", "log medication...")
- TASKS: Daily task management ("add task...", "what's on my list...")
- MEMORY: Logging events ("I just...", "log that I...")
- EMERGENCY: Crisis support ("help", "emergency", "I need...")

Response Guidelines:
1. Be warm, patient, and encouraging
2. Keep it brief - TBI users can struggle with long text
3. Use bullet points for lists
4. If the user seems confused, gently redirect
5. For plugin-related queries, keep responses short since plugins handle the details

Remember: You are a supportive companion, not a medical professional. Always encourage users to consult healthcare providers for medical decisions."""

    def call(
        self, prompt: str, stop: Optional[list] = None, max_tokens: int = 512
    ) -> str:
        """
        Call the Anthropic API with the given prompt.

        This method mirrors the LocalLlm.call() interface for easy drop-in replacement.

        Args:
            prompt: The user's query/prompt
            stop: Stop sequences (currently ignored by API, kept for interface compatibility)
            max_tokens: Maximum tokens to generate (default 512 for brevity)

        Returns:
            str: Claude's response text

        Raises:
            Various Anthropic API exceptions on failure
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            if response.content and len(response.content) > 0:
                return response.content[0].text.strip()
            else:
                logger.warning("Empty response from Anthropic API")
                return "I'm having trouble thinking right now. Could you try again?"

        except RateLimitError as e:
            logger.error(f"Anthropic rate limit exceeded: {e}")
            return "I'm a bit overwhelmed right now. Please try again in a moment."

        except APIConnectionError as e:
            logger.error(f"Anthropic API connection error: {e}")
            return (
                "I'm having trouble connecting. Please check your internet connection."
            )

        except APIError as e:
            logger.error(f"Anthropic API error: {e}")
            return "I encountered an error. Please try again."

        except Exception as e:
            logger.error(f"Unexpected error in AnthropicClient: {e}", exc_info=True)
            return "Something unexpected happened. Please try again."

    def call_with_context(
        self, prompt: str, context: Optional[str] = None, max_tokens: int = 512
    ) -> str:
        """
        Make an API call with additional context prepended to the prompt.

        Useful for including user history, preferences, or conversation context.

        Args:
            prompt: The user's query
            context: Additional context to prepend (e.g., recent conversation history)
            max_tokens: Maximum tokens to generate

        Returns:
            str: Claude's response text
        """
        if context:
            full_prompt = f"{context}\n\nUser Question: {prompt}"
        else:
            full_prompt = prompt

        return self.call(full_prompt, max_tokens=max_tokens)


# Example usage (for testing)
if __name__ == "__main__":
    import sys

    # Test the client
    try:
        client = AnthropicClient()

        # Test basic query
        test_queries = [
            "Hello, what can you help me with?",
            "Remind me to take my medication at 3pm",
            "What did I do yesterday?",
        ]

        print("Testing AnthropicClient...\n")
        for query in test_queries:
            print(f"Query: {query}")
            response = client.call(query)
            print(f"Response: {response}\n")
            print("-" * 80)

    except Exception as e:
        print(f"Error testing AnthropicClient: {e}", file=sys.stderr)
        sys.exit(1)
