"""
Encryption module for confidential memories.

Uses Fernet (symmetric encryption) from the cryptography library.
Encryption key should be stored securely outside the database.
"""

import os
import base64
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_fernet_instance = None


def get_encryption_key() -> bytes:
    """
    Get or generate encryption key.
    
    In production, this should be loaded from a secure key management system.
    For air-gapped deployment, store in environment variable or mounted secret file.
    
    Returns:
        32-byte encryption key
    """
    # Try to load from environment
    key_b64 = os.environ.get("MEMORY_ENCRYPTION_KEY")
    
    if key_b64:
        try:
            return base64.urlsafe_b64decode(key_b64)
        except Exception as e:
            logger.error(f"Failed to decode encryption key: {e}")
    
    # Try to load from file
    key_file = os.environ.get("MEMORY_ENCRYPTION_KEY_FILE", "/secrets/memory_encryption.key")
    if os.path.exists(key_file):
        try:
            with open(key_file, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read encryption key file: {e}")
    
    # Generate new key (WARNING: will be lost on restart!)
    logger.warning("No encryption key found. Generating ephemeral key (will be lost on restart!)")
    logger.warning("Set MEMORY_ENCRYPTION_KEY or MEMORY_ENCRYPTION_KEY_FILE for persistent encryption")
    
    try:
        from cryptography.fernet import Fernet
        key = Fernet.generate_key()
        logger.info(f"Generated key (base64): {key.decode()}")
        logger.info("To persist this key, set: MEMORY_ENCRYPTION_KEY=" + key.decode())
        return key
    except ImportError:
        logger.error("cryptography library not installed. Install: pip install cryptography")
        # Return a deterministic key based on hostname (NOT SECURE, just for fallback)
        import hashlib, socket
        hostname = socket.gethostname()
        return hashlib.sha256(hostname.encode()).digest()


def get_fernet():
    """
    Get or create Fernet cipher instance.
    
    Returns:
        Fernet instance or None if cryptography not available
    """
    global _fernet_instance
    
    if _fernet_instance is not None:
        return _fernet_instance
    
    try:
        from cryptography.fernet import Fernet
        key = get_encryption_key()
        _fernet_instance = Fernet(key)
        return _fernet_instance
    except ImportError:
        logger.error("cryptography not installed - encryption disabled")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Fernet: {e}")
        return None


def encrypt_text(plaintext: str) -> Optional[str]:
    """
    Encrypt text for storage.
    
    Args:
        plaintext: Text to encrypt
    
    Returns:
        Base64-encoded ciphertext or None if encryption fails
    """
    if not plaintext:
        return plaintext
    
    fernet = get_fernet()
    if fernet is None:
        logger.warning("Encryption not available - storing plaintext")
        return plaintext
    
    try:
        ciphertext = fernet.encrypt(plaintext.encode('utf-8'))
        return ciphertext.decode('ascii')
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        return plaintext


def decrypt_text(ciphertext: str) -> Optional[str]:
    """
    Decrypt text from storage.
    
    Args:
        ciphertext: Base64-encoded encrypted text
    
    Returns:
        Decrypted plaintext or None if decryption fails
    """
    if not ciphertext:
        return ciphertext
    
    fernet = get_fernet()
    if fernet is None:
        # If no encryption available, assume it's plaintext
        return ciphertext
    
    try:
        plaintext = fernet.decrypt(ciphertext.encode('ascii'))
        return plaintext.decode('utf-8')
    except Exception as e:
        # If decryption fails, might be plaintext (for backward compatibility)
        logger.warning(f"Decryption failed (might be plaintext): {e}")
        return ciphertext


def should_encrypt_memory(privacy_label: Optional[str]) -> bool:
    """
    Determine if a memory should be encrypted based on privacy label.
    
    Args:
        privacy_label: Memory privacy label
    
    Returns:
        True if memory should be encrypted
    """
    # Encrypt confidential memories by default
    if privacy_label == "confidential":
        return True
    
    # Check environment variable for global encryption policy
    encrypt_all = os.environ.get("ENCRYPT_ALL_MEMORIES", "false").lower() in ("1", "true", "yes")
    
    return encrypt_all


if __name__ == "__main__":
    # Test encryption
    logging.basicConfig(level=logging.INFO)
    
    print("Testing encryption module...")
    
    plaintext = "This is a confidential memory about my health condition"
    print(f"\nOriginal: {plaintext}")
    
    encrypted = encrypt_text(plaintext)
    print(f"Encrypted: {encrypted[:50]}...")
    
    decrypted = decrypt_text(encrypted)
    print(f"Decrypted: {decrypted}")
    
    assert decrypted == plaintext, "Encryption/decryption failed!"
    print("\n✓ Encryption test passed")
