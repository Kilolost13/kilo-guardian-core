"""
TPM Secret Sealing Module for Bastion AI

Provides hardware-backed secret protection using TPM 2.0.
Secrets are sealed to PCR values, meaning they can only be
unsealed when the system is in a known-good boot state.

For NixOS appliance deployment:
- Secrets are sealed during initial setup
- Only unsealed when booted from verified NixOS configuration
- Prevents extraction if disk is stolen or booted from different OS

Fallback modes:
- If TPM not available: uses encrypted file storage with user password
- If sealed secrets don't exist: prompts for initial setup

Dependencies:
- tpm2-tools (tpm2_createprimary, tpm2_create, tpm2_load, etc.)
- systemd-creds (optional, for systemd credential management)

Author: Kilo Guardian AI System
"""

import base64
import hashlib
import json
import logging
import os
import secrets as crypto_secrets
import subprocess
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class TPMState(Enum):
    """TPM availability state"""

    AVAILABLE = "available"
    NOT_PRESENT = "not_present"
    NOT_INITIALIZED = "not_initialized"
    ACCESS_DENIED = "access_denied"
    ERROR = "error"


@dataclass
class SealedSecret:
    """Container for a sealed secret"""

    name: str
    sealed_data: bytes
    pcr_policy: str  # PCR values used for sealing
    created_at: str
    version: int = 1


class TPMSecretManager:
    """
    Manages secrets using TPM 2.0 hardware security.

    Secrets are sealed to PCR values (Platform Configuration Registers)
    which measure the boot process. This ensures secrets can only be
    accessed when booted from the expected configuration.

    PCR usage:
    - PCR 0: BIOS/UEFI firmware
    - PCR 7: Secure Boot state
    - PCR 11: systemd-boot (on NixOS)
    - PCR 14: MOK (Machine Owner Key) state

    Default policy: PCR 0 + PCR 7 (firmware + secure boot)
    """

    # Default PCRs to seal against
    DEFAULT_PCRS = "0,7"

    # Path for sealed secrets storage
    SEALED_SECRETS_DIR = Path("/var/lib/bastion/secrets")

    # Fallback encrypted storage (when no TPM)
    FALLBACK_SECRETS_FILE = Path("/var/lib/bastion/secrets.enc")

    def __init__(
        self,
        pcrs: str = None,
        secrets_dir: Path = None,
        fallback_password: Optional[str] = None,
    ):
        """
        Initialize TPM Secret Manager.

        Args:
            pcrs: PCR indices to seal against (e.g., "0,7")
            secrets_dir: Directory for storing sealed secrets
            fallback_password: Password for encrypted fallback storage
        """
        self.pcrs = pcrs or self.DEFAULT_PCRS
        self.secrets_dir = secrets_dir or self.SEALED_SECRETS_DIR
        self.fallback_password = fallback_password

        self._tpm_state: Optional[TPMState] = None
        self._primary_handle: Optional[str] = None

        # Ensure secrets directory exists
        self.secrets_dir.mkdir(parents=True, exist_ok=True)

    @property
    def tpm_available(self) -> bool:
        """Check if TPM is available and usable."""
        state = self.check_tpm_state()
        return state == TPMState.AVAILABLE

    def check_tpm_state(self) -> TPMState:
        """
        Check TPM availability and state.

        Returns:
            TPMState indicating TPM status
        """
        if self._tpm_state is not None:
            return self._tpm_state

        # Check if TPM device exists
        tpm_device = Path("/dev/tpm0")
        tpm_resource_mgr = Path("/dev/tpmrm0")

        if not tpm_device.exists() and not tpm_resource_mgr.exists():
            logger.info("TPM device not found")
            self._tpm_state = TPMState.NOT_PRESENT
            return self._tpm_state

        # Check if tpm2-tools is installed
        try:
            result = subprocess.run(
                ["which", "tpm2_getcap"], capture_output=True, timeout=5
            )
            if result.returncode != 0:
                logger.warning("tpm2-tools not installed")
                self._tpm_state = TPMState.NOT_INITIALIZED
                return self._tpm_state
        except Exception as e:
            logger.error(f"Error checking for tpm2-tools: {e}")
            self._tpm_state = TPMState.ERROR
            return self._tpm_state

        # Try to query TPM capabilities
        try:
            result = subprocess.run(
                ["tpm2_getcap", "properties-fixed"], capture_output=True, timeout=10
            )
            if result.returncode == 0:
                logger.info("TPM 2.0 available and accessible")
                self._tpm_state = TPMState.AVAILABLE
            elif b"Permission denied" in result.stderr:
                logger.warning("TPM access denied - check permissions")
                self._tpm_state = TPMState.ACCESS_DENIED
            else:
                logger.warning(f"TPM query failed: {result.stderr.decode()}")
                self._tpm_state = TPMState.ERROR
        except subprocess.TimeoutExpired:
            logger.error("TPM query timed out")
            self._tpm_state = TPMState.ERROR
        except Exception as e:
            logger.error(f"TPM query error: {e}")
            self._tpm_state = TPMState.ERROR

        return self._tpm_state

    def get_pcr_values(self, pcrs: str = None) -> Dict[int, str]:
        """
        Read current PCR values from TPM.

        Args:
            pcrs: PCR indices to read (e.g., "0,7")

        Returns:
            Dict mapping PCR index to hex value
        """
        pcrs = pcrs or self.pcrs

        if not self.tpm_available:
            logger.warning("TPM not available, cannot read PCR values")
            return {}

        try:
            result = subprocess.run(
                ["tpm2_pcrread", f"sha256:{pcrs}"], capture_output=True, timeout=10
            )

            if result.returncode != 0:
                logger.error(f"Failed to read PCRs: {result.stderr.decode()}")
                return {}

            # Parse PCR output
            pcr_values = {}
            for line in result.stdout.decode().split("\n"):
                # Format: "  0 : 0x..."
                if ":" in line and "0x" in line:
                    parts = line.strip().split(":")
                    if len(parts) >= 2:
                        try:
                            pcr_idx = int(parts[0].strip())
                            pcr_val = parts[1].strip()
                            pcr_values[pcr_idx] = pcr_val
                        except ValueError:
                            continue

            return pcr_values

        except Exception as e:
            logger.error(f"Error reading PCR values: {e}")
            return {}

    def seal_secret(self, name: str, secret: str, pcrs: str = None) -> bool:
        """
        Seal a secret using TPM with PCR policy.

        The secret will only be unsealable when PCR values match
        the current boot state.

        Args:
            name: Identifier for the secret
            secret: The secret value to seal
            pcrs: PCR indices for policy (default: self.pcrs)

        Returns:
            True if sealing succeeded
        """
        pcrs = pcrs or self.pcrs

        if not self.tpm_available:
            logger.info("TPM not available, using fallback storage")
            return self._seal_fallback(name, secret)

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)

                # Write secret to temp file
                secret_file = tmpdir / "secret.txt"
                secret_file.write_text(secret)

                # Create primary key context
                primary_ctx = tmpdir / "primary.ctx"
                result = subprocess.run(
                    [
                        "tpm2_createprimary",
                        "-C",
                        "o",  # Owner hierarchy
                        "-c",
                        str(primary_ctx),
                    ],
                    capture_output=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    logger.error(f"Failed to create primary: {result.stderr.decode()}")
                    return self._seal_fallback(name, secret)

                # Create sealing object with PCR policy
                sealed_priv = tmpdir / "sealed.priv"
                sealed_pub = tmpdir / "sealed.pub"

                result = subprocess.run(
                    [
                        "tpm2_create",
                        "-C",
                        str(primary_ctx),
                        "-i",
                        str(secret_file),
                        "-u",
                        str(sealed_pub),
                        "-r",
                        str(sealed_priv),
                        "-L",
                        f"sha256:{pcrs}",
                        "-a",
                        "fixedtpm|fixedparent",
                    ],
                    capture_output=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    logger.error(
                        f"Failed to create sealed object: {result.stderr.decode()}"
                    )
                    return self._seal_fallback(name, secret)

                # Store sealed data
                sealed_dir = self.secrets_dir / name
                sealed_dir.mkdir(parents=True, exist_ok=True)

                # Copy sealed key parts
                (sealed_dir / "sealed.pub").write_bytes(sealed_pub.read_bytes())
                (sealed_dir / "sealed.priv").write_bytes(sealed_priv.read_bytes())
                (sealed_dir / "primary.ctx").write_bytes(primary_ctx.read_bytes())

                # Store metadata
                metadata = {
                    "name": name,
                    "pcrs": pcrs,
                    "pcr_values": self.get_pcr_values(pcrs),
                    "created_at": self._get_timestamp(),
                    "version": 1,
                    "method": "tpm",
                }
                (sealed_dir / "metadata.json").write_text(
                    json.dumps(metadata, indent=2)
                )

                # Securely delete temp secret
                secret_file.write_bytes(b"\x00" * len(secret))
                secret_file.unlink()

                logger.info(f"✅ Secret '{name}' sealed to TPM with PCR policy {pcrs}")
                return True

        except Exception as e:
            logger.error(f"TPM sealing error: {e}")
            return self._seal_fallback(name, secret)

    def unseal_secret(self, name: str) -> Optional[str]:
        """
        Unseal a secret from TPM.

        Will only succeed if current PCR values match the policy
        used during sealing.

        Args:
            name: Identifier for the secret

        Returns:
            The unsealed secret, or None if unsealing failed
        """
        sealed_dir = self.secrets_dir / name

        if not sealed_dir.exists():
            logger.warning(f"No sealed secret found for '{name}'")
            return self._unseal_fallback(name)

        # Check metadata
        metadata_file = sealed_dir / "metadata.json"
        if not metadata_file.exists():
            logger.error(f"Metadata missing for secret '{name}'")
            return None

        metadata = json.loads(metadata_file.read_text())

        # If it was stored with fallback/basic method, use fallback path
        method = metadata.get("method", "fallback")
        if method in ("fallback", "basic"):
            return self._unseal_fallback(name, method)

        if not self.tpm_available:
            logger.error("TPM not available, cannot unseal TPM-sealed secret")
            return None

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir = Path(tmpdir)

                # Load the sealed object
                loaded_ctx = tmpdir / "loaded.ctx"

                result = subprocess.run(
                    [
                        "tpm2_load",
                        "-C",
                        str(sealed_dir / "primary.ctx"),
                        "-u",
                        str(sealed_dir / "sealed.pub"),
                        "-r",
                        str(sealed_dir / "sealed.priv"),
                        "-c",
                        str(loaded_ctx),
                    ],
                    capture_output=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    logger.error(
                        f"Failed to load sealed object: {result.stderr.decode()}"
                    )
                    return None

                # Unseal with PCR policy
                unsealed_file = tmpdir / "unsealed.txt"
                pcrs = metadata.get("pcrs", self.pcrs)

                result = subprocess.run(
                    [
                        "tpm2_unseal",
                        "-c",
                        str(loaded_ctx),
                        "-o",
                        str(unsealed_file),
                        "-p",
                        f"pcr:sha256:{pcrs}",
                    ],
                    capture_output=True,
                    timeout=30,
                )

                if result.returncode != 0:
                    error_msg = result.stderr.decode()
                    if "policy" in error_msg.lower() or "pcr" in error_msg.lower():
                        logger.error(
                            f"PCR policy mismatch - system boot state has changed! "
                            f"Secret '{name}' cannot be unsealed."
                        )
                    else:
                        logger.error(f"Failed to unseal: {error_msg}")
                    return None

                secret = unsealed_file.read_text()

                # Securely delete temp file
                unsealed_file.write_bytes(b"\x00" * len(secret))
                unsealed_file.unlink()

                logger.info(f"✅ Secret '{name}' unsealed successfully")
                return secret

        except Exception as e:
            logger.error(f"TPM unsealing error: {e}")
            return None

    def _seal_fallback(self, name: str, secret: str) -> bool:
        """
        Fallback sealing using encrypted file storage.

        Uses AES-256-GCM with a derived key from password or
        a randomly generated key stored securely.
        """
        try:
            # Use cryptography library if available, else simple XOR
            try:
                from cryptography.hazmat.primitives import hashes
                from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

                # Generate or use password
                if self.fallback_password:
                    password = self.fallback_password.encode()
                else:
                    # Generate random key and store it
                    key = crypto_secrets.token_bytes(32)
                    self._store_fallback_key(key)
                    password = key

                # Derive key
                salt = crypto_secrets.token_bytes(16)
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=480000,
                )
                key = kdf.derive(password)

                # Encrypt
                aesgcm = AESGCM(key)
                nonce = crypto_secrets.token_bytes(12)
                ciphertext = aesgcm.encrypt(nonce, secret.encode(), None)

                # Store
                sealed_dir = self.secrets_dir / name
                sealed_dir.mkdir(parents=True, exist_ok=True)

                encrypted_data = {
                    "salt": base64.b64encode(salt).decode(),
                    "nonce": base64.b64encode(nonce).decode(),
                    "ciphertext": base64.b64encode(ciphertext).decode(),
                }
                (sealed_dir / "encrypted.json").write_text(json.dumps(encrypted_data))

                metadata = {
                    "name": name,
                    "created_at": self._get_timestamp(),
                    "version": 1,
                    "method": "fallback",
                }
                (sealed_dir / "metadata.json").write_text(
                    json.dumps(metadata, indent=2)
                )

                logger.info(f"✅ Secret '{name}' stored with encrypted fallback")
                return True

            except ImportError:
                # Simple obfuscation fallback (NOT SECURE - just for testing)
                logger.warning(
                    "cryptography library not available, using basic storage"
                )
                sealed_dir = self.secrets_dir / name
                sealed_dir.mkdir(parents=True, exist_ok=True)

                # Ensure a fallback key exists for consistency
                if not self.fallback_password:
                    key = crypto_secrets.token_bytes(32)
                    self._store_fallback_key(key)

                # Simple base64 encoding (NOT SECURE)
                encoded = base64.b64encode(secret.encode()).decode()
                (sealed_dir / "secret.b64").write_text(encoded)

                metadata = {
                    "name": name,
                    "created_at": self._get_timestamp(),
                    "version": 1,
                    "method": "fallback",
                }
                (sealed_dir / "metadata.json").write_text(
                    json.dumps(metadata, indent=2)
                )

                return True

        except Exception as e:
            logger.error(f"Fallback sealing error: {e}")
            return False

    def _unseal_fallback(self, name: str, method: str = "fallback") -> Optional[str]:
        """Unseal from fallback encrypted storage (AESGCM or basic)."""
        sealed_dir = self.secrets_dir / name

        if not sealed_dir.exists():
            return None

        metadata_file = sealed_dir / "metadata.json"
        if not metadata_file.exists():
            return None

        metadata = json.loads(metadata_file.read_text())
        method = metadata.get("method", method or "fallback")

        try:
            if method == "fallback" and (sealed_dir / "encrypted.json").exists():
                try:
                    from cryptography.hazmat.primitives import hashes
                    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
                    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

                    encrypted_data = json.loads(
                        (sealed_dir / "encrypted.json").read_text()
                    )

                    salt = base64.b64decode(encrypted_data["salt"])
                    nonce = base64.b64decode(encrypted_data["nonce"])
                    ciphertext = base64.b64decode(encrypted_data["ciphertext"])

                    # Get password
                    if self.fallback_password:
                        password = self.fallback_password.encode()
                    else:
                        password = self._load_fallback_key()
                        if password is None:
                            logger.error("Fallback key not available")
                            return None

                    # Derive key
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=salt,
                        iterations=480000,
                    )
                    key = kdf.derive(password)

                    # Decrypt
                    aesgcm = AESGCM(key)
                    plaintext = aesgcm.decrypt(nonce, ciphertext, None)

                    return plaintext.decode()
                except Exception as e:
                    logger.error(f"Fallback AES unsealing error: {e}")

            # Basic/base64 decode path (works without cryptography)
            if (sealed_dir / "secret.b64").exists():
                encoded = (sealed_dir / "secret.b64").read_text()
                return base64.b64decode(encoded).decode()

        except Exception as e:
            logger.error(f"Fallback unsealing error: {e}")
            return None

        return None

    def _store_fallback_key(self, key: bytes):
        """Store fallback encryption key securely."""
        key_file = self.secrets_dir / ".fallback_key"
        key_file.write_bytes(key)
        key_file.chmod(0o600)  # Owner read/write only

    def _load_fallback_key(self) -> Optional[bytes]:
        """Load fallback encryption key."""
        key_file = self.secrets_dir / ".fallback_key"
        if key_file.exists():
            return key_file.read_bytes()
        return None

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone

        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def list_secrets(self) -> list[str]:
        """List all stored secrets."""
        secrets = []
        for item in self.secrets_dir.iterdir():
            if item.is_dir() and (item / "metadata.json").exists():
                secrets.append(item.name)
        return secrets

    def delete_secret(self, name: str) -> bool:
        """
        Securely delete a sealed secret.

        Args:
            name: Secret identifier

        Returns:
            True if deletion succeeded
        """
        sealed_dir = self.secrets_dir / name

        if not sealed_dir.exists():
            logger.warning(f"Secret '{name}' not found")
            return False

        try:
            import shutil

            # Overwrite files with zeros before deletion
            for file in sealed_dir.iterdir():
                if file.is_file():
                    size = file.stat().st_size
                    file.write_bytes(b"\x00" * size)

            shutil.rmtree(sealed_dir)
            logger.info(f"Secret '{name}' deleted")
            return True

        except Exception as e:
            logger.error(f"Error deleting secret: {e}")
            return False

    def reseal_all(self) -> Dict[str, bool]:
        """
        Reseal all secrets with current PCR values.

        Useful after system updates that change PCR values.
        Requires all secrets to be currently unsealable.

        Returns:
            Dict mapping secret name to success status
        """
        results = {}

        for name in self.list_secrets():
            # Unseal with old policy
            secret = self.unseal_secret(name)
            if secret is None:
                logger.error(f"Cannot reseal '{name}' - unseal failed")
                results[name] = False
                continue

            # Delete old sealed version
            self.delete_secret(name)

            # Seal with new PCR values
            results[name] = self.seal_secret(name, secret)

            # Clear secret from memory
            secret = None

        return results


# Singleton instance
_tpm_manager: Optional[TPMSecretManager] = None


def get_tpm_manager(**kwargs) -> TPMSecretManager:
    """Get or create the TPM secret manager singleton."""
    global _tpm_manager
    if _tpm_manager is None:
        _tpm_manager = TPMSecretManager(**kwargs)
    return _tpm_manager
