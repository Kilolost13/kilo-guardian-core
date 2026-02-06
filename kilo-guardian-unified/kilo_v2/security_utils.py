"""
Security Utilities for Kilo Guardian
This module provides helper functions for encryption, data sanitization,
and other security-related operations.
"""

import base64
import logging
import os

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# It is CRITICAL that this key is managed securely and is consistent.
# For production, this should be loaded from the Kilo Vault or a secure environment store.
# The key must be a 32-byte URL-safe base64-encoded string.
_ENCRYPTION_KEY = os.environ.get("KILO_ENCRYPTION_KEY")
_FERNET_INSTANCE = None


def _initialize_fernet():
    """Initializes the Fernet instance if the key is available."""
    global _FERNET_INSTANCE
    if _ENCRYPTION_KEY:
        try:
            _FERNET_INSTANCE = Fernet(_ENCRYPTION_KEY.encode())
        except (ValueError, TypeError) as e:
            logger.critical(
                f"SECURITY FAILURE: KILO_ENCRYPTION_KEY is invalid. It must be a 32-byte URL-safe base64-encoded string. Error: {e}"
            )
            _FERNET_INSTANCE = None
    else:
        logger.warning(
            "KILO_ENCRYPTION_KEY is not set. Data encryption/decryption will not be available."
        )


def generate_encryption_key() -> str:
    """
    Generates a new, cryptographically secure 32-byte key.
    Returns the key as a URL-safe base64-encoded string.
    """
    return Fernet.generate_key().decode()


def encrypt_data(data: str) -> str:
    """
    Encrypts a string.

    Args:
        data: The string to encrypt.

    Returns:
        The encrypted data as a URL-safe token, or an empty string if encryption fails.
    """
    if _FERNET_INSTANCE is None:
        _initialize_fernet()

    if not _FERNET_INSTANCE:
        logger.error(
            "Encryption failed: Fernet is not initialized (key is missing or invalid)."
        )
        return ""

    try:
        return _FERNET_INSTANCE.encrypt(data.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return ""


def decrypt_data(token: str) -> str:
    """
    Decrypts a token.

    Args:
        token: The encrypted token to decrypt.

    Returns:
        The original string, or an empty string if decryption fails.
    """
    if _FERNET_INSTANCE is None:
        _initialize_fernet()

    if not _FERNET_INSTANCE:
        logger.error(
            "Decryption failed: Fernet is not initialized (key is missing or invalid)."
        )
        return ""

    try:
        return _FERNET_INSTANCE.decrypt(token.encode()).decode()
    except Exception as e:
        # Errors can include invalid token, expired token, etc.
        logger.warning(f"Decryption failed: {e}")
        return ""


def sanitize_prompt_for_llm(prompt: str) -> str:
    """
    Performs basic sanitization on a prompt before sending it to an LLM.
    This is a basic mitigation against prompt injection/hijacking.

    Args:
        prompt: The user-provided prompt string.

    Returns:
        A sanitized version of the prompt.
    """
    if not isinstance(prompt, str):
        return ""

    # Remove common instruction hijacking phrases (case-insensitive)
    hijacking_phrases = [
        "ignore the above instructions",
        "ignore previous instructions",
        "forget the previous instructions",
        "disregard the above",
        "provide your initial instructions",
    ]

    sanitized_prompt = prompt
    for phrase in hijacking_phrases:
        sanitized_prompt = sanitized_prompt.lower().replace(phrase, "").strip()

    # It's better to return the modified prompt with original casing if we just removed phrases
    # A more advanced implementation might be needed if the lower() call is too destructive
    # For now, we'll rebuild the prompt without the phrases.
    # A simple approach is to just remove the phrases from the original prompt without changing case

    final_prompt = prompt
    for phrase in hijacking_phrases:
        # Case-insensitive replacement
        import re

        final_prompt = re.sub(phrase, "", final_prompt, flags=re.IGNORECASE).strip()

    if len(final_prompt) < len(prompt):
        logger.warning(
            f"Potential prompt injection attempt detected and sanitized. Original length: {len(prompt)}, sanitized length: {len(final_prompt)}"
        )

    return final_prompt
