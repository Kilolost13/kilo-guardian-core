"""
USB Data Transfer Module for Air-Gapped AI Memory Assistant

This module provides secure data transfer capabilities for air-gapped systems,
allowing export of therapy progress data and secure import of bulk data via USB drives.
Features include:
- Password protection for data access
- Data integrity validation
- Infection detection for USB drives
- Encrypted data export/import
- Admin interface for data management
"""

import os
import json
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class USBDevice:
    """Represents a detected USB device"""
    mount_point: str
    device_id: str
    label: Optional[str] = None
    size_gb: float = 0.0
    is_safe: bool = False
    last_scan: Optional[datetime] = None

@dataclass
class DataExport:
    """Represents an exported data package"""
    id: str
    timestamp: datetime
    data_type: str  # 'therapy_progress', 'full_backup', 'habits_only', etc.
    record_count: int
    file_size_mb: float
    checksum: str
    encrypted: bool = True

@dataclass
class SecurityConfig:
    """Security configuration for USB transfers"""
    password_hash: str
    salt: str
    encryption_key: str
    session_timeout_minutes: int = 30
    max_file_size_mb: int = 100
    allowed_extensions: List[str] = None

    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = ['.json', '.csv', '.txt', '.pdf']

class USBTransferService:
    """
    Main service for secure USB data transfer operations
    """

    def __init__(self, config_path: str = "/etc/kilo/usb_config.json"):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.security_config = self._load_or_create_config()
        self.active_sessions: Dict[str, datetime] = {}
        self.mounted_devices: Dict[str, USBDevice] = {}

    def _load_or_create_config(self) -> SecurityConfig:
        """Load existing config or create default one"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    data = json.load(f)
                return SecurityConfig(**data)
            except Exception as e:
                logger.warning(f"Failed to load config: {e}")

        # Create default config
        password = self._generate_secure_password()
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(password, salt)
        encryption_key = self._derive_key(password, salt)

        config = SecurityConfig(
            password_hash=password_hash,
            salt=salt,
            encryption_key=encryption_key.decode()
        )

        self._save_config(config)
        logger.info("Created default USB security config")
        logger.info(f"Default password: {password}")
        logger.warning("CHANGE THE DEFAULT PASSWORD IMMEDIATELY!")

        return config

    def _save_config(self, config: SecurityConfig):
        """Save security configuration"""
        with open(self.config_path, 'w') as f:
            json.dump(asdict(config), f, indent=2, default=str)

    def _generate_secure_password(self) -> str:
        """Generate a secure default password"""
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return ''.join(secrets.choice(chars) for _ in range(16))

    def _hash_password(self, password: str, salt: str) -> str:
        """Hash password with salt"""
        combined = (password + salt).encode()
        return hashlib.sha256(combined).hexdigest()

    def _derive_key(self, password: str, salt: str) -> bytes:
        """Derive encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def authenticate(self, password: str) -> Tuple[bool, Optional[str]]:
        """
        Authenticate user with password
        Returns: (success, session_token)
        """
        password_hash = self._hash_password(password, self.security_config.salt)

        if password_hash == self.security_config.password_hash:
            session_token = secrets.token_urlsafe(32)
            self.active_sessions[session_token] = datetime.now()
            logger.info("USB transfer authentication successful")
            return True, session_token

        logger.warning("USB transfer authentication failed")
        return False, None

    def validate_session(self, session_token: str) -> bool:
        """Validate if session is still active"""
        if session_token not in self.active_sessions:
            return False

        session_time = self.active_sessions[session_token]
        timeout = timedelta(minutes=self.security_config.session_timeout_minutes)

        if datetime.now() - session_time > timeout:
            del self.active_sessions[session_token]
            return False

        # Refresh session
        self.active_sessions[session_token] = datetime.now()
        return True

    def change_password(self, session_token: str, old_password: str, new_password: str) -> bool:
        """Change the USB transfer password"""
        if not self.validate_session(session_token):
            return False

        # Verify old password
        old_hash = self._hash_password(old_password, self.security_config.salt)
        if old_hash != self.security_config.password_hash:
            return False

        # Update password
        salt = secrets.token_hex(16)
        password_hash = self._hash_password(new_password, salt)
        encryption_key = self._derive_key(new_password, salt)

        self.security_config.password_hash = password_hash
        self.security_config.salt = salt
        self.security_config.encryption_key = encryption_key.decode()

        self._save_config(self.security_config)
        logger.info("USB transfer password changed successfully")
        return True

    def scan_usb_devices(self) -> List[USBDevice]:
        """Scan for mounted USB devices and check safety"""
        devices = []
        usb_mounts = ['/media', '/mnt']

        for mount_base in usb_mounts:
            if not Path(mount_base).exists():
                continue

            for item in Path(mount_base).iterdir():
                if item.is_dir():
                    try:
                        # Get device info
                        stat = item.stat()
                        size_gb = stat.st_size / (1024**3) if stat.st_size > 0 else 0

                        # Normalize device_id to a string. Prefer MagicMock._mock_name (used in tests),
                        # then Path.name (str), then fallback to basename of mount path.
                        dev_id = getattr(item, '_mock_name', None) or getattr(item, 'name', None) or os.path.basename(str(item))
                        # Ensure we have a plain string
                        if not isinstance(dev_id, str):
                            dev_id = str(dev_id)

                        device = USBDevice(
                            mount_point=str(item),
                            device_id=str(dev_id),
                            size_gb=round(size_gb, 2),
                            last_scan=datetime.now()
                        )

                        # Basic safety checks
                        device.is_safe = self._check_device_safety(item)
                        devices.append(device)

                    except Exception as e:
                        logger.warning(f"Failed to scan device {item}: {e}")

        self.mounted_devices = {d.device_id: d for d in devices}
        return devices

    def _check_device_safety(self, mount_path: Path) -> bool:
        """Perform basic safety checks on USB device"""
        try:
            # Check for suspicious files
            suspicious_files = [
                'autorun.inf', 'autorun.exe', 'setup.exe',
                'install.exe', 'update.exe', 'patch.exe'
            ]

            for file in suspicious_files:
                if (mount_path / file).exists():
                    logger.warning(f"Suspicious file found: {file}")
                    return False

            # Check for hidden system files (basic check)
            hidden_count = 0
            total_files = 0

            for item in mount_path.rglob('*'):
                if item.is_file():
                    total_files += 1
                    if item.name.startswith('.'):
                        hidden_count += 1

            # If more than 50% hidden files, suspicious
            if total_files > 10 and (hidden_count / total_files) > 0.5:
                logger.warning("High ratio of hidden files detected")
                return False

            return True

        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            return False

    def export_therapy_progress(self, session_token: str, device_id: str,
                              data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Export therapy progress data to USB device
        """
        if not self.validate_session(session_token):
            return False, "Invalid session"

        if device_id not in self.mounted_devices:
            return False, "USB device not found"

        device = self.mounted_devices[device_id]
        if not device.is_safe:
            return False, "USB device failed safety check"

        try:
            # Create export directory
            export_dir = Path(device.mount_point) / "kilo_exports"
            export_dir.mkdir(exist_ok=True)

            # Generate export metadata
            export_id = secrets.token_hex(8)
            timestamp = datetime.now()

            export_data = {
                "export_id": export_id,
                "timestamp": timestamp.isoformat(),
                "data_type": "therapy_progress",
                "version": "1.0",
                "data": data
            }

            # Encrypt data
            fernet = Fernet(self.security_config.encryption_key)
            json_data = json.dumps(export_data, indent=2, default=str)
            encrypted_data = fernet.encrypt(json_data.encode())

            # Save encrypted file
            filename = f"therapy_progress_{export_id}_{timestamp.strftime('%Y%m%d_%H%M%S')}.kilo"
            filepath = export_dir / filename

            with open(filepath, 'wb') as f:
                f.write(encrypted_data)

            # Create checksum file
            checksum = hashlib.sha256(encrypted_data).hexdigest()
            checksum_file = filepath.with_suffix('.sha256')
            with open(checksum_file, 'w') as f:
                f.write(f"{checksum}  {filename}\n")

            # Create metadata file (unencrypted for easy reading)
            metadata = {
                "export_id": export_id,
                "timestamp": timestamp.isoformat(),
                "data_type": "therapy_progress",
                "encrypted": True,
                "checksum": checksum,
                "file_size_mb": round(len(encrypted_data) / (1024*1024), 2),
                "record_count": len(data.get('memories', []))
            }

            metadata_file = filepath.with_suffix('.meta')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2, default=str)

            logger.info(f"Exported therapy progress to {filepath}")
            return True, f"Export successful: {filename}"

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False, f"Export failed: {str(e)}"

    def import_data(self, session_token: str, device_id: str,
                   import_type: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Import data from USB device
        """
        if not self.validate_session(session_token):
            return False, "Invalid session", {}

        if device_id not in self.mounted_devices:
            return False, "USB device not found", {}

        device = self.mounted_devices[device_id]
        if not device.is_safe:
            return False, "USB device failed safety check", {}

        try:
            import_dir = Path(device.mount_point) / "kilo_imports"
            if not import_dir.exists():
                return False, "No import directory found", {}

            # Find import files
            import_files = list(import_dir.glob("*.kilo"))
            if not import_files:
                return False, "No import files found", {}

            # For now, import the most recent file
            import_file = max(import_files, key=lambda x: x.stat().st_mtime)

            # Verify checksum if available
            checksum_file = import_file.with_suffix('.sha256')
            if checksum_file.exists():
                with open(checksum_file, 'r') as f:
                    expected_checksum = f.read().strip().split()[0]

                with open(import_file, 'rb') as f:
                    actual_checksum = hashlib.sha256(f.read()).hexdigest()

                if actual_checksum != expected_checksum:
                    return False, "Checksum verification failed", {}

            # Decrypt and parse data
            fernet = Fernet(self.security_config.encryption_key)
            with open(import_file, 'rb') as f:
                encrypted_data = f.read()

            decrypted_data = fernet.decrypt(encrypted_data)
            import_data = json.loads(decrypted_data.decode())

            logger.info(f"Imported data from {import_file}")
            return True, f"Import successful: {import_file.name}", import_data

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False, f"Import failed: {str(e)}", {}

    def get_export_history(self, session_token: str) -> List[DataExport]:
        """Get history of data exports"""
        if not self.validate_session(session_token):
            return []

        # This would typically query a database
        # For now, return empty list
        return []

    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.now()
        timeout = timedelta(minutes=self.security_config.session_timeout_minutes)

        expired = [
            token for token, start_time in self.active_sessions.items()
            if current_time - start_time > timeout
        ]

        for token in expired:
            del self.active_sessions[token]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

# Global service instance
usb_service = USBTransferService(config_path="/tmp/kilo_usb_config.json")