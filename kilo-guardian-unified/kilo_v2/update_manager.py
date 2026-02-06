"""
Update Manager for Kilo's Bastion Appliance
Handles secure, signed updates with verification and rollback
"""

import base64
import hashlib
import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Public key path for Ed25519 signature verification
PUBLIC_KEY_PATH = "/etc/kilo/release-public-key.pem"
UPDATE_CHECK_URL = "https://updates.example.com/kilo/stable/manifest.json"

# Legacy SSH key for backwards compatibility
UPDATE_PUBLIC_KEY = """ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIGOwvmrW42H7t5GmvsqSfWjaShF0A0rE+46JJ5gZL74A Bastion Update Key"""


class UpdateVerificationError(Exception):
    """Raised when update verification fails."""

    pass


def verify_manifest_signature(
    manifest: dict, public_key_path: str = PUBLIC_KEY_PATH
) -> bool:
    """
    Verify Ed25519 signature on update manifest (for NixOS ISO updates).

    Args:
        manifest: Parsed manifest dict with 'signature' field
        public_key_path: Path to Ed25519 public key PEM

    Returns:
        True if signature is valid

    Raises:
        UpdateVerificationError: If signature format is invalid
    """
    signature_field = manifest.get("signature", "")
    if not signature_field.startswith("ed25519:"):
        raise UpdateVerificationError(
            "Invalid signature format (must be 'ed25519:base64')"
        )

    sig_b64 = signature_field.split(":", 1)[1]

    # Reconstruct canonical manifest (without signature field)
    manifest_copy = {k: v for k, v in manifest.items() if k != "signature"}
    canonical = json.dumps(manifest_copy, sort_keys=True, separators=(",", ":"))

    # Verify with openssl
    try:
        # Write signature to temp file
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as sig_file:
            sig_file.write(base64.b64decode(sig_b64))
            sig_path = sig_file.name

        try:
            proc = subprocess.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-verify",
                    "-pubin",
                    "-inkey",
                    public_key_path,
                    "-sigfile",
                    sig_path,
                ],
                input=canonical.encode(),
                capture_output=True,
                check=False,
            )

            # openssl returns 0 for success
            if proc.returncode == 0:
                logger.info("✓ Manifest signature verification passed")
                return True
            else:
                logger.error(
                    f"Manifest signature verification failed: {proc.stderr.decode()}"
                )
                return False

        finally:
            Path(sig_path).unlink()

    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


def verify_iso_checksum(iso_path: str, expected_sha256: str) -> bool:
    """
    Verify ISO file integrity via SHA256 checksum.

    Args:
        iso_path: Path to ISO file
        expected_sha256: Expected SHA256 hex digest

    Returns:
        True if checksum matches
    """
    logger.info(f"Verifying ISO checksum: {iso_path}")
    sha256 = hashlib.sha256()

    try:
        with open(iso_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)

        computed = sha256.hexdigest()
        if computed != expected_sha256:
            logger.error(f"Checksum mismatch!")
            logger.error(f"  Expected: {expected_sha256}")
            logger.error(f"  Got:      {computed}")
            return False

        logger.info("✓ ISO checksum verified")
        return True

    except Exception as e:
        logger.error(f"Checksum verification failed: {e}")
        return False


def apply_nixos_update(iso_path: str) -> bool:
    """
    Apply NixOS update by mounting ISO and rebuilding.

    Args:
        iso_path: Path to verified ISO file

    Returns:
        True if update applied successfully (reboot required)
    """
    mount_point = "/mnt/update-iso"
    Path(mount_point).mkdir(parents=True, exist_ok=True)

    try:
        # Mount ISO
        logger.info(f"Mounting {iso_path}...")
        subprocess.run(
            ["sudo", "mount", "-o", "loop,ro", iso_path, mount_point],
            check=True,
            capture_output=True,
        )

        # Rebuild from ISO flake
        logger.info("Applying update (this may take several minutes)...")
        proc = subprocess.run(
            ["sudo", "nixos-rebuild", "boot", "--flake", f"{mount_point}#kilo"],
            capture_output=True,
            check=False,
        )

        if proc.returncode != 0:
            logger.error(f"nixos-rebuild failed:\n{proc.stderr.decode()}")
            return False

        logger.info("✓ Update applied successfully")
        logger.info("⚠ Reboot required to activate new generation")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"Update failed: {e.stderr.decode() if e.stderr else str(e)}")
        return False
    except Exception as e:
        logger.error(f"Update failed: {e}")
        return False
    finally:
        # Unmount
        try:
            subprocess.run(
                ["sudo", "umount", mount_point], check=False, capture_output=True
            )
        except Exception:
            pass


def rollback_nixos_update() -> bool:
    """
    Rollback to previous NixOS generation.

    Returns:
        True if rollback successful
    """
    try:
        logger.info("Rolling back to previous generation...")
        proc = subprocess.run(
            ["sudo", "nixos-rebuild", "switch", "--rollback"],
            capture_output=True,
            check=False,
        )

        if proc.returncode != 0:
            logger.error(f"Rollback failed:\n{proc.stderr.decode()}")
            return False

        logger.info("✓ Rollback complete")
        return True

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False


def list_nixos_generations() -> list:
    """
    List available NixOS generations for rollback.

    Returns:
        List of generation dicts with id, date, current flag
    """
    try:
        proc = subprocess.run(
            [
                "nix-env",
                "--list-generations",
                "--profile",
                "/nix/var/nix/profiles/system",
            ],
            capture_output=True,
            check=True,
            text=True,
        )

        generations = []
        for line in proc.stdout.splitlines():
            # Parse "  42   2025-12-05 10:30:15   (current)"
            parts = line.strip().split(maxsplit=2)
            if len(parts) >= 2:
                gen_id = parts[0]
                gen_date = parts[1] if len(parts) > 1 else ""
                is_current = "(current)" in line
                generations.append(
                    {"id": gen_id, "date": gen_date, "current": is_current}
                )

        return generations

    except Exception as e:
        logger.error(f"Failed to list generations: {e}")
        return []


class UpdateManager:
    """Manages appliance updates with cryptographic verification"""

    def __init__(self, bastion_root: Optional[str] = None):
        # Use environment variable or default to /opt/bastion
        if bastion_root:
            self.bastion_root = Path(bastion_root)
        else:
            self.bastion_root = Path(os.getenv("BASTION_ROOT", "/opt/bastion"))

        self.update_dir = self.bastion_root / "updates"
        self.backup_dir = self.bastion_root / "backups"
        self.current_version = self._get_current_version()

        # Create directories only if bastion_root exists or we can create it
        try:
            self.bastion_root.mkdir(parents=True, exist_ok=True)
            self.update_dir.mkdir(exist_ok=True)
            self.backup_dir.mkdir(exist_ok=True)
        except PermissionError:
            logger.warning(
                f"Cannot create directories in {self.bastion_root} (permission denied)"
            )
        except Exception as e:
            logger.warning(f"Could not create update directories: {e}")

        # Update server URL (can be local or remote)
        self.update_server = os.getenv(
            "UPDATE_SERVER_URL", "https://kiloscasket.com/api/updates"
        )
        self.check_enabled = (
            os.getenv("UPDATE_CHECK_ENABLED", "false").lower() == "true"
        )

        logger.info(f"UpdateManager initialized: v{self.current_version}")
        logger.info(f"Update server: {self.update_server}")
        logger.info(f"Auto-check: {self.check_enabled}")

    def _get_current_version(self) -> str:
        """Get current appliance version from VERSION file"""
        version_file = self.bastion_root / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return "1.0.0"

    def check_for_updates(self, license_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Check if updates are available.
        Returns dict with update info or None if up to date.
        """
        try:
            import requests

            params = {
                "current_version": self.current_version,
                "hardware_id": self._get_hardware_id(),
            }

            if license_key:
                params["license"] = license_key

            logger.info(f"Checking for updates: v{self.current_version}")

            response = requests.get(
                f"{self.update_server}/check", params=params, timeout=10
            )

            if response.status_code == 200:
                data = response.json()

                if data.get("update_available"):
                    logger.info(f"Update available: v{data['version']}")
                    return {
                        "available": True,
                        "version": data["version"],
                        "download_url": data["download_url"],
                        "signature_url": data["signature_url"],
                        "changelog": data.get("changelog", "No changelog provided"),
                        "size_mb": data.get("size_mb", 0),
                        "release_date": data.get("release_date"),
                    }
                else:
                    logger.info("No updates available")
                    return {"available": False, "message": "Up to date"}

            return {
                "available": False,
                "error": f"Server returned {response.status_code}",
            }

        except Exception as e:
            logger.error(f"Update check failed: {e}")
            return {"available": False, "error": str(e)}

    def download_update(self, download_url: str, signature_url: str) -> Optional[Path]:
        """
        Download update package and signature.
        Returns path to downloaded package or None on failure.
        """
        try:
            import requests

            # Extract version from URL
            version = download_url.split("_v")[1].split(".bai")[0]
            package_path = self.update_dir / f"update_v{version}.bai"
            signature_path = self.update_dir / f"update_v{version}.bai.sig"

            logger.info(f"Downloading update v{version}...")

            # Download package
            response = requests.get(download_url, stream=True, timeout=60)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(package_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            progress = (downloaded / total_size) * 100
                            if progress % 10 < 1:  # Log every 10%
                                logger.info(f"Download progress: {progress:.0f}%")

            logger.info(f"Package downloaded: {package_path}")

            # Download signature
            response = requests.get(signature_url, timeout=10)
            response.raise_for_status()
            signature_path.write_bytes(response.content)

            logger.info(f"Signature downloaded: {signature_path}")

            return package_path

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return None

    def verify_update(self, package_path: Path) -> bool:
        """
        Verify update package signature.
        Returns True if signature is valid.
        """
        try:
            signature_path = package_path.with_suffix(".bai.sig")

            if not signature_path.exists():
                logger.error("Signature file not found")
                return False

            # Write public key to temp file
            key_file = Path("/tmp/bastion_update_key.pub")
            key_file.write_text(UPDATE_PUBLIC_KEY)

            logger.info("Verifying update signature...")

            # Verify with ssh-keygen
            result = subprocess.run(
                [
                    "ssh-keygen",
                    "-Y",
                    "verify",
                    "-f",
                    str(key_file),
                    "-I",
                    "bastion",
                    "-n",
                    "bastion",
                    "-s",
                    str(signature_path),
                ],
                stdin=open(package_path, "rb"),
                capture_output=True,
            )

            key_file.unlink()  # Cleanup

            if result.returncode == 0:
                logger.info("✅ Signature verification PASSED")
                return True
            else:
                logger.error(
                    f"❌ Signature verification FAILED: {result.stderr.decode()}"
                )
                return False

        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False

    def _run_sql_migrations(self, migration_file: Path) -> bool:
        """
        Run SQL migrations from a migration file.

        Migration file format:
        - Plain SQL statements separated by semicolons
        - Comments start with -- or /* */
        - Supports multiple databases (looks for DB path comments)

        Example migration.sql:
            -- DB: kilo_guardian_keep.db
            ALTER TABLE events ADD COLUMN priority INTEGER DEFAULT 0;

            -- DB: finance.db
            CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date);
        """
        import sqlite3

        try:
            migration_sql = migration_file.read_text()

            # Default database paths
            db_paths = {
                "kilo_guardian_keep.db": self.bastion_root / "kilo_guardian_keep.db",
                "finance.db": self.bastion_root / "finance.db",
                "bastion_users.db": self.bastion_root / "bastion_users.db",
            }

            current_db = "kilo_guardian_keep.db"  # Default
            statements_run = 0

            # Parse and run migrations
            for line in migration_sql.split("\n"):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("/*"):
                    continue

                # Check for database switch directive
                if line.startswith("-- DB:"):
                    db_name = line.split(":", 1)[1].strip()
                    if db_name in db_paths:
                        current_db = db_name
                        logger.info(f"Switching to database: {current_db}")
                    continue

                # Skip other comments
                if line.startswith("--"):
                    continue

                # Execute SQL statement
                db_path = db_paths.get(current_db)
                if db_path and db_path.exists():
                    try:
                        conn = sqlite3.connect(str(db_path))
                        cursor = conn.cursor()
                        cursor.execute(line)
                        conn.commit()
                        conn.close()
                        statements_run += 1
                    except sqlite3.Error as sql_err:
                        # Log but continue - some statements might fail if already applied
                        logger.warning(f"Migration statement warning: {sql_err}")

            logger.info(f"✅ Ran {statements_run} migration statements")
            return True

        except Exception as e:
            logger.error(f"Migration error: {e}")
            return False

    def create_backup(self) -> Optional[Path]:
        """
        Create backup of current installation.
        Returns path to backup file.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_v{self.current_version}_{timestamp}.tar.gz"
            backup_path = self.backup_dir / backup_name

            logger.info(f"Creating backup: {backup_name}")

            # Backup critical directories
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(self.bastion_root / "kilo_v2", arcname="kilo_v2")
                tar.add(self.bastion_root / "VERSION", arcname="VERSION")

                # Backup database if exists
                db_file = self.bastion_root / "bastion_users.db"
                if db_file.exists():
                    tar.add(db_file, arcname="bastion_users.db")

                # Backup config
                config_dir = self.bastion_root / "config"
                if config_dir.exists():
                    tar.add(config_dir, arcname="config")

            logger.info(
                f"✅ Backup created: {backup_path} ({backup_path.stat().st_size / 1024 / 1024:.1f}MB)"
            )

            # Keep only last 5 backups
            self._cleanup_old_backups(keep=5)

            return backup_path

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    def apply_update(self, package_path: Path) -> bool:
        """
        Apply update package.
        Returns True on success, False on failure (with automatic rollback).
        """
        backup_path = None

        try:
            # 1. Create backup
            logger.info("Step 1: Creating backup...")
            backup_path = self.create_backup()
            if not backup_path:
                raise Exception("Backup creation failed")

            # 2. Extract package
            logger.info("Step 2: Extracting update package...")
            extract_dir = self.update_dir / "extracted"
            extract_dir.mkdir(exist_ok=True)

            with tarfile.open(package_path, "r") as tar:
                # Use filter='data' for security (Python 3.12+) or fallback
                try:
                    tar.extractall(extract_dir, filter="data")
                except TypeError:
                    # Python < 3.12 doesn't support filter argument
                    tar.extractall(extract_dir)

            # 3. Read manifest
            manifest_file = extract_dir / "manifest.json"
            if not manifest_file.exists():
                raise Exception("Invalid update: manifest.json not found")

            manifest = json.loads(manifest_file.read_text())
            new_version = manifest["version"]

            logger.info(f"Step 3: Applying update v{new_version}...")

            # 4. Run pre-update script if exists
            pre_script = extract_dir / "pre_update.sh"
            if pre_script.exists():
                logger.info("Running pre-update script...")
                subprocess.run(["bash", str(pre_script)], check=True)

            # 5. Copy files
            logger.info("Step 4: Copying files...")

            # Update kilo_v2
            if (extract_dir / "kilo_v2").exists():
                shutil.copytree(
                    extract_dir / "kilo_v2",
                    self.bastion_root / "kilo_v2",
                    dirs_exist_ok=True,
                )

            # Update plugins
            if (extract_dir / "plugins").exists():
                shutil.copytree(
                    extract_dir / "plugins",
                    self.bastion_root / "kilo_v2" / "plugins",
                    dirs_exist_ok=True,
                )

            # 6. Install dependencies if needed
            if (extract_dir / "requirements.txt").exists():
                logger.info("Step 5: Installing dependencies...")
                subprocess.run(
                    [
                        self.bastion_root / ".venv" / "bin" / "pip",
                        "install",
                        "-r",
                        str(extract_dir / "requirements.txt"),
                    ],
                    check=True,
                )

            # 7. Run database migrations if needed
            if (extract_dir / "migration.sql").exists():
                logger.info("Step 6: Running database migrations...")
                self._run_sql_migrations(extract_dir / "migration.sql")

            # 8. Run post-update script if exists
            post_script = extract_dir / "post_update.sh"
            if post_script.exists():
                logger.info("Running post-update script...")
                subprocess.run(["bash", str(post_script)], check=True)

            # 9. Update VERSION file
            logger.info("Step 7: Updating version...")
            version_file = self.bastion_root / "VERSION"
            version_file.write_text(new_version)

            # 10. Cleanup
            shutil.rmtree(extract_dir)

            logger.info(
                f"✅ Update applied successfully: v{self.current_version} → v{new_version}"
            )
            logger.info("Restart required for changes to take effect")

            return True

        except Exception as e:
            logger.error(f"❌ Update failed: {e}")

            # Rollback
            if backup_path:
                logger.warning("Attempting rollback...")
                if self.rollback(backup_path):
                    logger.info("✅ Rollback successful")
                else:
                    logger.error("❌ Rollback failed - manual recovery needed")

            return False

    def rollback(self, backup_path: Path) -> bool:
        """
        Rollback to previous backup.
        Returns True on success.
        """
        try:
            logger.info(f"Rolling back to: {backup_path}")

            with tarfile.open(backup_path, "r:gz") as tar:
                # Use filter='data' for security (Python 3.12+) or fallback
                try:
                    tar.extractall(self.bastion_root, filter="data")
                except TypeError:
                    # Python < 3.12 doesn't support filter argument
                    tar.extractall(self.bastion_root)

            logger.info("✅ Rollback complete")
            return True

        except Exception as e:
            logger.error(f"Rollback error: {e}")
            return False

    def install_from_usb(self, usb_path: Path) -> bool:
        """
        Install update from USB drive.
        Looks for .bai file and .bai.sig in USB root.
        """
        try:
            # Find .bai files
            bai_files = list(usb_path.glob("*.bai"))

            if not bai_files:
                logger.error("No .bai update files found on USB")
                return False

            if len(bai_files) > 1:
                logger.warning(f"Multiple .bai files found, using: {bai_files[0]}")

            package_path = bai_files[0]
            signature_path = package_path.with_suffix(".bai.sig")

            if not signature_path.exists():
                logger.error(f"Signature file not found: {signature_path}")
                return False

            # Copy to update directory
            dest_package = self.update_dir / package_path.name
            dest_signature = self.update_dir / signature_path.name

            shutil.copy(package_path, dest_package)
            shutil.copy(signature_path, dest_signature)

            logger.info(f"Copied update from USB: {package_path.name}")

            # Verify and apply
            if self.verify_update(dest_package):
                return self.apply_update(dest_package)
            else:
                logger.error("Update verification failed")
                return False

        except Exception as e:
            logger.error(f"USB install failed: {e}")
            return False

    def _cleanup_old_backups(self, keep: int = 5):
        """Keep only the most recent N backups"""
        backups = sorted(
            self.backup_dir.glob("backup_*.tar.gz"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for old_backup in backups[keep:]:
            logger.info(f"Removing old backup: {old_backup.name}")
            old_backup.unlink()

    def _get_hardware_id(self) -> str:
        """Get appliance hardware ID"""
        hw_file = self.bastion_root / ".hardware_id"
        if hw_file.exists():
            return hw_file.read_text().strip()

        # Generate hardware ID
        import uuid

        mac = ":".join(
            [
                "{:02x}".format((uuid.getnode() >> ele) & 0xFF)
                for ele in range(0, 8 * 6, 8)
            ][::-1]
        )

        hardware_id = hashlib.sha256(mac.encode()).hexdigest()[:16]
        hw_file.write_text(hardware_id)

        return hardware_id

    def get_status(self) -> Dict[str, Any]:
        """Get update manager status"""
        return {
            "current_version": self.current_version,
            "update_server": self.update_server,
            "check_enabled": self.check_enabled,
            "backups_count": len(list(self.backup_dir.glob("backup_*.tar.gz"))),
            "hardware_id": self._get_hardware_id(),
        }


# Global instance - only create in production environment
if os.getenv("KILO_ENV", "development") == "production" or os.path.exists(
    "/opt/bastion"
):
    try:
        update_manager = UpdateManager()
    except Exception as e:
        logger.warning(f"UpdateManager initialization failed: {e}")
        update_manager = None
else:
    # Development mode - don't auto-create
    update_manager = None
    logger.info("UpdateManager not initialized (development mode)")
