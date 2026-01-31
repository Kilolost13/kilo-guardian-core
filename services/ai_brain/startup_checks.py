"""
Startup validation for air-gapped deployment.

Checks that all required models and dependencies are available
before starting the service.
"""

import os
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def check_embedding_model() -> bool:
    """Check if sentence-transformers model is available."""
    try:
        from .embeddings import get_embedding_model
        model = get_embedding_model()
        if model is not None:
            logger.info("✓ Embedding model loaded successfully")
            return True
        else:
            logger.warning("⚠ Embedding model not available - using fallback")
            return False
    except Exception as e:
        logger.warning(f"⚠ Could not load embedding model: {e}")
        return False


def check_ollama_binary() -> bool:
    """Check if Ollama binary is available for local LLM."""
    from shutil import which
    
    ollama_bin = os.environ.get("OLLAMA_BIN") or which("ollama")
    
    if ollama_bin and os.path.exists(ollama_bin):
        logger.info(f"✓ Ollama binary found: {ollama_bin}")
        return True
    else:
        logger.warning("⚠ Ollama binary not found - LLM features will be limited")
        logger.warning("  Install Ollama: https://ollama.ai")
        return False


def check_tesseract() -> bool:
    """Check if Tesseract OCR is available."""
    from shutil import which
    
    tesseract_bin = which("tesseract")
    
    if tesseract_bin:
        logger.info(f"✓ Tesseract OCR found: {tesseract_bin}")
        return True
    else:
        logger.warning("⚠ Tesseract not found - OCR features will fail")
        return False


def check_network_mode() -> bool:
    """Check network mode and warn if providers require network."""
    from .utils.network import allow_network
    
    network_enabled = allow_network()
    stt_provider = os.environ.get("STT_PROVIDER", "none")
    tts_provider = os.environ.get("TTS_PROVIDER", "none")
    
    logger.info(f"Network mode: {'ENABLED' if network_enabled else 'DISABLED (air-gapped)'}")
    logger.info(f"STT provider: {stt_provider}")
    logger.info(f"TTS provider: {tts_provider}")
    
    # Warn if external providers configured but network disabled
    if not network_enabled:
        if stt_provider in ("openai",):
            logger.error(f"✗ STT provider '{stt_provider}' requires network but ALLOW_NETWORK=false")
            return False
        if tts_provider in ("gtts",):
            logger.error(f"✗ TTS provider '{tts_provider}' requires network but ALLOW_NETWORK=false")
            return False
        
        logger.info("✓ Air-gapped mode configured correctly")
    
    return True


def check_dependencies() -> bool:
    """Check optional dependencies."""
    deps_status = {}
    
    # sentence-transformers
    try:
        import sentence_transformers
        deps_status['sentence-transformers'] = True
    except ImportError:
        deps_status['sentence-transformers'] = False
        logger.warning("⚠ sentence-transformers not installed - using fallback embeddings")
        logger.warning("  Install: pip install sentence-transformers")
    
    # cryptography (for encryption)
    try:
        import cryptography
        deps_status['cryptography'] = True
    except ImportError:
        deps_status['cryptography'] = False
        logger.warning("⚠ cryptography not installed - memory encryption disabled")
        logger.warning("  Install: pip install cryptography")
    
    # bcrypt (for secure token hashing)
    try:
        import bcrypt
        deps_status['bcrypt'] = True
    except ImportError:
        deps_status['bcrypt'] = False
        logger.warning("⚠ bcrypt not installed - using less secure SHA256 for tokens")
        logger.warning("  Install: pip install bcrypt")
    
    return True  # Optional dependencies don't fail startup


def check_model_paths() -> bool:
    """Check if model directories exist."""
    model_base = Path("/app/models")
    
    if not model_base.exists():
        logger.warning(f"⚠ Models directory not found: {model_base}")
        logger.warning("  Models will be downloaded on first use (requires network)")
        logger.warning("  For air-gapped deployment, run: tools/package_models.sh")
        return False
    
    # Check for specific model directories
    checks = {
        "sentence_transformers": model_base / "sentence_transformers",
        "tesseract": model_base / "tesseract",
        "mediapipe": model_base / "mediapipe",
    }
    
    all_present = True
    for name, path in checks.items():
        if path.exists():
            logger.info(f"✓ {name} models found: {path}")
        else:
            logger.warning(f"⚠ {name} models not found: {path}")
            all_present = False
    
    return all_present


def run_startup_checks(fail_on_error: bool = False) -> bool:
    """
    Run all startup checks.
    
    Args:
        fail_on_error: If True, exit with error code if critical checks fail
    
    Returns:
        True if all checks passed, False otherwise
    """
    logger.info("=" * 60)
    logger.info("KILO AI MEMORY ASSISTANT - Startup Checks")
    logger.info("=" * 60)
    
    checks = {
        "Network Configuration": check_network_mode(),
        "Dependencies": check_dependencies(),
        "Embedding Model": check_embedding_model(),
        "Ollama LLM": check_ollama_binary(),
        "Tesseract OCR": check_tesseract(),
        "Model Paths": check_model_paths(),
    }
    
    logger.info("=" * 60)
    logger.info("Startup Check Summary:")
    
    all_passed = True
    for check_name, passed in checks.items():
        status = "✓ PASS" if passed else "⚠ WARN"
        logger.info(f"  {status}: {check_name}")
        if not passed and check_name == "Network Configuration":
            all_passed = False
    
    logger.info("=" * 60)
    
    if not all_passed and fail_on_error:
        logger.error("Critical startup checks failed - exiting")
        sys.exit(1)
    
    if all_passed:
        logger.info("✓ All checks passed - service ready")
    else:
        logger.warning("⚠ Some checks failed - service will run with limited functionality")
    
    return all_passed


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    run_startup_checks(fail_on_error=True)
