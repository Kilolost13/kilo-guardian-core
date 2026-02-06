"""
Secure Credential Manager for Bastion AI
Handles loading, validation, and secure access to sensitive credentials

Supports three credential sources (in priority order):
1. TPM-sealed secrets (hardware-backed, most secure)
2. Environment variables
3. .env file (development only)

For production NixOS deployments, credentials should be sealed
to TPM after initial setup for hardware-backed protection.
"""

import logging
import os
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# TPM integration - imported lazily to avoid circular imports
_tpm_manager = None


@dataclass
class Credentials:
    """Container for application credentials"""

    # API Keys
    kilo_api_key: str
    gemini_api_key: str

    # Google OAuth
    google_credentials_path: Optional[Path] = None
    google_token_path: Optional[Path] = None

    # External APIs
    openweather_api_key: Optional[str] = None
    news_api_key: Optional[str] = None

    # Production settings
    environment: str = "development"
    domain: Optional[str] = None
    session_secret: Optional[str] = None

    # Email/SMTP
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    alert_email: Optional[str] = None

    # Stripe
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.environment.lower() in ("production", "prod")

    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.environment.lower() in ("development", "dev")

    def validate(self) -> list[str]:
        """
        Validate credentials and return list of warnings/errors.

        Returns:
            List of validation messages (empty if all OK)
        """
        issues = []

        # Check critical keys
        if not self.kilo_api_key:
            issues.append("CRITICAL: KILO_API_KEY not set!")
        elif self.kilo_api_key == "kilo-dev-key-2025":
            if self.is_production():
                issues.append("CRITICAL: Using default API key in production!")
            else:
                issues.append("WARNING: Using default development API key")

        # Only warn about Gemini/remote LLM if remote LLM usage is enabled via
        # env var
        try:
            use_remote = os.environ.get("USE_REMOTE_LLM", "false").lower() in (
                "1",
                "true",
                "yes",
                "on",
            )
        except Exception:
            use_remote = False
        if use_remote and not self.gemini_api_key:
            issues.append(
                ("WARNING: GEMINI_API_KEY not set " "(Remote LLM features disabled)")
            )

        # Production-specific checks
        if self.is_production():
            if not self.domain:
                issues.append("WARNING: DOMAIN not set (OAuth callbacks may fail)")

            if not self.session_secret:
                issues.append("CRITICAL: SESSION_SECRET not set in production!")

            # Check SSL settings
            ssl_cert = os.getenv("SSL_CERT_FILE")
            ssl_key = os.getenv("SSL_KEY_FILE")
            if not ssl_cert or not ssl_key:
                issues.append("WARNING: SSL certificates not configured")

        # Google OAuth checks
        if self.google_credentials_path:
            if not self.google_credentials_path.exists():
                issues.append(
                    "ERROR: Google credentials file not found: "
                    f"{self.google_credentials_path}"
                )
        else:
            issues.append(
                (
                    "INFO: Google OAuth not configured "
                    "(email/calendar features disabled)"
                )
            )

        return issues


class CredentialManager:
    """
    Manages secure loading and access to credentials.

    Credential sources (in priority order):
    1. TPM-sealed secrets (if available and USE_TPM_SECRETS=1)
    2. Environment variables (including from .env in dev)
    3. Default values (for development only)

    For production, call seal_to_tpm() after initial setup to
    protect credentials with hardware-backed security.
    """

    # Credential keys that can be sealed to TPM
    TPM_SEALABLE_KEYS = [
        "KILO_API_KEY",
        "GEMINI_API_KEY",
        "SESSION_SECRET",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "SMTP_PASSWORD",
        "OPENWEATHER_API_KEY",
        "NEWS_API_KEY",
    ]

    def __init__(self, env_file: Optional[str] = None, use_tpm: bool = None):
        """
        Initialize credential manager.

        Args:
            env_file: Path to .env file (default: searches for .env in parent
                dirs)
            use_tpm: Whether to use TPM for secrets (default: auto-detect)
        """
        self._credentials: Optional[Credentials] = None
        self._env_file = env_file
        self._tpm_manager = None
        self._use_tpm = use_tpm

        # Detect test mode early - skip .env loading during tests to allow
        # test code to control environment variables precisely
        self._is_testing = any("pytest" in str(a) for a in sys.argv) or bool(
            os.environ.get("PYTEST_RUNNING") or os.environ.get("PYTEST_CURRENT_TEST")
        )

        # Initialize TPM manager if enabled and not testing
        if not self._is_testing:
            self._init_tpm()
            self._load_env_file()
        else:
            logger.info("Test mode detected - skipping .env file and TPM")

    def _init_tpm(self):
        """Initialize TPM manager if available and enabled."""
        # Check if TPM should be used
        if self._use_tpm is None:
            # Auto-detect: use TPM if available and enabled via env var
            self._use_tpm = os.environ.get("USE_TPM_SECRETS", "0") == "1"

        if not self._use_tpm:
            logger.debug("TPM secrets disabled (USE_TPM_SECRETS not set)")
            return

        try:
            from kilo_v2.tpm_secrets import get_tpm_manager

            self._tpm_manager = get_tpm_manager()

            if self._tpm_manager.tpm_available:
                logger.info("✅ TPM available - hardware-backed secrets enabled")
            else:
                logger.info("TPM not available - using fallback encrypted storage")

        except ImportError as e:
            logger.warning(f"TPM module not available: {e}")
            self._tpm_manager = None
        except Exception as e:
            logger.error(f"Failed to initialize TPM: {e}")
            self._tpm_manager = None

    def _load_env_file(self):
        """Load environment variables from a secrets file if available."""

        candidates = []

        if self._env_file:
            candidates.append(Path(self._env_file).expanduser())
        else:
            # Highest priority: explicit path hint
            explicit = os.environ.get("BASTION_SECRET_FILE")
            if explicit:
                candidates.append(Path(explicit).expanduser())

            # Repository-level secrets drop zone (git-ignored)
            repo_root = Path(__file__).resolve().parent.parent
            candidates.append(repo_root / "secrets" / ".env.local")
            candidates.append(repo_root / "secrets" / ".env")

            # Backward compatibility: look for .env in cwd and parents
            current = Path.cwd()
            candidates.extend(
                parent / ".env" for parent in [current] + list(current.parents)
            )

        env_path = next(
            (p for p in candidates if p and p.exists() and p.is_file()), None
        )

        if env_path:
            logger.info(f"Loading environment from {env_path}")
            self._parse_env_file(env_path)
        else:
            logger.warning("No secrets file found - using environment variables only")

    def _parse_env_file(self, path: Path):
        """Parse .env file and set environment variables"""
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue

                    # Parse KEY=VALUE
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Remove quotes if present
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]

                        # Only set if not already in environment
                        if key not in os.environ:
                            os.environ[key] = value

        except Exception as e:
            logger.error(f"Failed to parse .env file: {e}")

    def _get_from_tpm(self, key: str) -> Optional[str]:
        """
        Try to get a credential from TPM-sealed storage.

        Args:
            key: The credential key (e.g., "KILO_API_KEY")

        Returns:
            The unsealed value, or None if not available
        """
        if not self._tpm_manager:
            return None

        try:
            # TPM secrets are stored with lowercase names
            secret_name = f"bastion_{key.lower()}"
            value = self._tpm_manager.unseal_secret(secret_name)

            if value:
                logger.debug(f"Loaded {key} from TPM-sealed storage")

            return value

        except Exception as e:
            logger.warning(f"Failed to load {key} from TPM: {e}")
            return None

    def _get_credential(self, key: str, default: str = None) -> Optional[str]:
        """
        Get a credential value, checking TPM first then environment.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Credential value from TPM, environment, or default
        """
        # Priority 1: TPM-sealed secrets (if enabled)
        if key in self.TPM_SEALABLE_KEYS:
            tpm_value = self._get_from_tpm(key)
            if tpm_value:
                return tpm_value

        # Priority 2: Environment variable
        env_value = os.getenv(key)
        if env_value:
            return env_value

        # Priority 3: Default value
        return default

    def load(self) -> Credentials:
        """
        Load credentials from TPM, environment variables, or defaults.

        Priority order:
        1. TPM-sealed secrets (most secure)
        2. Environment variables
        3. Default values (development only)

        Returns:
            Credentials object with all loaded values
        """
        if self._credentials:
            return self._credentials

        # Get base directory for file paths
        base_dir = Path(__file__).parent

        # Load Google OAuth paths
        google_creds_path = os.getenv("GOOGLE_CREDENTIALS_FILE")
        if google_creds_path:
            google_creds_path = Path(google_creds_path)
        else:
            # Default location
            default_creds = base_dir / "google_credentials.json"
            if default_creds.exists():
                google_creds_path = default_creds

        google_token_path = os.getenv("GOOGLE_TOKEN_FILE")
        if google_token_path:
            google_token_path = Path(google_token_path)
        else:
            google_token_path = base_dir / "google_token.json"

        # Generate or load session secret
        session_secret = self._get_credential("SESSION_SECRET")
        if not session_secret:
            session_secret = secrets.token_urlsafe(32)
            logger.warning(
                (
                    "SESSION_SECRET not set, generated random value "
                    "(will change on restart)"
                )
            )

        # Use test mode detected during init for default API key
        _default_api_key = "test-api-key" if self._is_testing else "kilo-dev-key-2025"

        # Load all credentials (TPM -> env -> default)
        self._credentials = Credentials(
            # Required - use _get_credential for TPM-sealable keys
            kilo_api_key=self._get_credential("KILO_API_KEY", _default_api_key),
            gemini_api_key=self._get_credential("GEMINI_API_KEY", ""),
            # Google OAuth (paths, not sealable)
            google_credentials_path=google_creds_path,
            google_token_path=google_token_path,
            # External APIs
            openweather_api_key=self._get_credential("OPENWEATHER_API_KEY"),
            news_api_key=self._get_credential("NEWS_API_KEY"),
            # Environment (not secret)
            environment=os.getenv("ENVIRONMENT", "development"),
            domain=os.getenv("DOMAIN"),
            session_secret=session_secret,
            # Email/SMTP
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_user=os.getenv("SMTP_USER"),
            smtp_password=self._get_credential("SMTP_PASSWORD"),
            alert_email=os.getenv("ALERT_EMAIL"),
            # Stripe
            stripe_secret_key=self._get_credential("STRIPE_SECRET_KEY"),
            stripe_webhook_secret=self._get_credential("STRIPE_WEBHOOK_SECRET"),
        )

        # Validate and log issues
        issues = self._credentials.validate()
        for issue in issues:
            if issue.startswith("CRITICAL"):
                logger.error(issue)
            elif issue.startswith("ERROR"):
                logger.error(issue)
            elif issue.startswith("WARNING"):
                logger.warning(issue)
            else:
                logger.info(issue)

        return self._credentials

    def get(self) -> Credentials:
        """Get loaded credentials (loads if not already loaded)"""
        if not self._credentials:
            return self.load()
        return self._credentials

    def reload(self) -> Credentials:
        """Force reload credentials from environment"""
        self._credentials = None
        return self.load()

    def mask_sensitive(self, value: Optional[str], show_chars: int = 4) -> str:
        """
        Mask sensitive string for logging.

        Args:
            value: The sensitive string to mask
            show_chars: Number of characters to show at start/end

        Returns:
            Masked string like "sk_t****abcd" or "[not set]"
        """
        if not value:
            return "[not set]"

        if len(value) <= show_chars * 2:
            return "*" * len(value)

        return f"{value[:show_chars]}****{value[-show_chars:]}"

    def log_status(self):
        """Log current credential status (safely, with masking)"""
        creds = self.get()

        logger.info("=== Credential Status ===")
        logger.info(f"Environment: {creds.environment}")
        logger.info(f"KILO_API_KEY: {self.mask_sensitive(creds.kilo_api_key)}")
        logger.info("GEMINI_API_KEY: " f"{self.mask_sensitive(creds.gemini_api_key)}")

        if creds.google_credentials_path:
            logger.info(
                "Google credentials: "
                f"{creds.google_credentials_path.name} "
                f"({'✓' if creds.google_credentials_path.exists() else '✗'})"
            )
        else:
            logger.info("Google credentials: Not configured")

        if creds.openweather_api_key:
            logger.info(
                "OpenWeather API: " f"{self.mask_sensitive(creds.openweather_api_key)}"
            )

        if creds.stripe_secret_key:
            logger.info("Stripe: " f"{self.mask_sensitive(creds.stripe_secret_key)}")

        if creds.is_production():
            logger.info(f"Domain: {creds.domain or '[not set]'}")
            logger.info("SSL: " f"{os.getenv('SSL_CERT_FILE', '[not configured]')}")

        # Log TPM status
        if self._tpm_manager:
            status = "Available" if self._tpm_manager.tpm_available else "Fallback mode"
            logger.info("TPM: " f"{status}")
            sealed_secrets = self._tpm_manager.list_secrets()
            if sealed_secrets:
                logger.info(f"TPM-sealed secrets: {len(sealed_secrets)}")

        logger.info("========================")

    # =========================================================================
    # TPM Integration Methods
    # =========================================================================

    def seal_to_tpm(self, keys: list[str] = None) -> Dict[str, bool]:
        """
        Seal current credentials to TPM for hardware-backed protection.

        This should be called during initial setup after verifying
        credentials work correctly. Once sealed, credentials will be
        loaded from TPM on subsequent boots.

        Args:
            keys: List of credential keys to seal (default: all sealable)

        Returns:
            Dict mapping key names to success status
        """
        if not self._tpm_manager:
            logger.error("TPM manager not initialized. Set USE_TPM_SECRETS=1")
            return {}

        keys = keys or self.TPM_SEALABLE_KEYS
        creds = self.get()
        results = {}

        # Map credential keys to values
        key_values = {
            "KILO_API_KEY": creds.kilo_api_key,
            "GEMINI_API_KEY": creds.gemini_api_key,
            "SESSION_SECRET": creds.session_secret,
            "STRIPE_SECRET_KEY": creds.stripe_secret_key,
            "STRIPE_WEBHOOK_SECRET": creds.stripe_webhook_secret,
            "SMTP_PASSWORD": creds.smtp_password,
            "OPENWEATHER_API_KEY": creds.openweather_api_key,
            "NEWS_API_KEY": creds.news_api_key,
        }

        for key in keys:
            value = key_values.get(key)
            if not value:
                logger.debug(f"Skipping {key} - not set")
                results[key] = False
                continue

            secret_name = f"bastion_{key.lower()}"
            success = self._tpm_manager.seal_secret(secret_name, value)
            results[key] = success

            if success:
                logger.info(f"✅ Sealed {key} to TPM")
            else:
                logger.error(f"❌ Failed to seal {key}")

        return results

    def unseal_from_tpm(self, keys: list[str] = None) -> Dict[str, str]:
        """
        Unseal credentials from TPM (for verification/testing).

        Args:
            keys: List of credential keys to unseal (default: all sealable)

        Returns:
            Dict mapping key names to unsealed values
        """
        if not self._tpm_manager:
            logger.error("TPM manager not initialized")
            return {}

        keys = keys or self.TPM_SEALABLE_KEYS
        results = {}

        for key in keys:
            secret_name = f"bastion_{key.lower()}"
            value = self._tpm_manager.unseal_secret(secret_name)
            if value:
                results[key] = value

        return results

    def list_sealed_secrets(self) -> list[str]:
        """List all TPM-sealed secret names."""
        if not self._tpm_manager:
            return []
        return self._tpm_manager.list_secrets()

    def reseal_all(self) -> Dict[str, bool]:
        """
        Reseal all TPM secrets with current PCR values.

        Useful after system updates that change boot measurements.
        Must be run while current secrets are still unsealable.

        Returns:
            Dict mapping secret names to success status
        """
        if not self._tpm_manager:
            logger.error("TPM manager not initialized")
            return {}

        return self._tpm_manager.reseal_all()

    @property
    def tpm_available(self) -> bool:
        """Check if TPM is available for secret storage."""
        if not self._tpm_manager:
            return False
        return self._tpm_manager.tpm_available

    @property
    def tpm_enabled(self) -> bool:
        """Check if TPM secret storage is enabled."""
        return self._use_tpm and self._tpm_manager is not None

        logger.info("========================")


# Global instance
credential_manager = CredentialManager()


# Convenience function for quick access
def get_credentials() -> Credentials:
    """Get the global credentials instance"""
    return credential_manager.get()
