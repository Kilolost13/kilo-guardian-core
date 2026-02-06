"""
Secure Settings Manager for Kilo Guardian
Protects critical settings with PIN/password, prevents unauthorized changes.
"""

import hashlib
import json
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from plugins.base_plugin import BasePlugin


class SecureSettings(BasePlugin):
    """
    Secure settings management with parent/admin lock.
    Prevents children or unauthorized users from changing critical settings.
    """

    def __init__(self):
        super().__init__()
        self.db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "user_data",
            "secure_settings.db",
        )
        self._init_database()
        self._load_lock_status()

    def _init_database(self):
        """Initialize secure settings database."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Admin credentials table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_credentials (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                pin_hash TEXT,
                password_hash TEXT,
                salt TEXT NOT NULL,
                security_question TEXT,
                security_answer_hash TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_changed TEXT
            )
        """
        )

        # Protected settings table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS protected_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT,
                protection_level TEXT DEFAULT 'medium',
                last_modified TEXT,
                modified_by TEXT
            )
        """
        )

        # Access log table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                setting_key TEXT,
                success INTEGER,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                ip_address TEXT,
                user_agent TEXT
            )
        """
        )

        # Session tokens table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_sessions (
                token TEXT PRIMARY KEY,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                expires_at TEXT NOT NULL,
                ip_address TEXT
            )
        """
        )

        # Check if admin is set up
        cursor.execute("SELECT COUNT(*) FROM admin_credentials WHERE id = 1")
        if cursor.fetchone()[0] == 0:
            # Generate a secure random salt
            salt = secrets.token_hex(32)
            # No credentials set yet - insert placeholder
            cursor.execute(
                "INSERT INTO admin_credentials (id, salt) VALUES (1, ?)", (salt,)
            )

        conn.commit()
        conn.close()

    def _load_lock_status(self):
        """Load current lock status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT pin_hash, password_hash FROM admin_credentials WHERE id = 1"
        )
        result = cursor.fetchone()
        conn.close()

        self.is_locked = bool(result and (result[0] or result[1]))

    def get_name(self) -> str:
        return "secure_settings"

    def get_keywords(self) -> list:
        return [
            "settings",
            "security",
            "lock",
            "unlock",
            "password",
            "pin",
            "admin",
            "parent",
            "parental",
            "protect",
            "authorization",
        ]

    def run(self, query: str) -> dict:
        """Main execution method."""
        query_lower = query.lower()

        try:
            # Setup admin access
            if "setup" in query_lower and (
                "admin" in query_lower or "lock" in query_lower
            ):
                return self._handle_setup_admin()

            # Check lock status
            if "status" in query_lower or "is locked" in query_lower:
                return self._get_lock_status()

            # Unlock/authenticate
            if "unlock" in query_lower or "authenticate" in query_lower:
                return self._handle_unlock()

            # Change PIN/password
            if "change" in query_lower and (
                "pin" in query_lower or "password" in query_lower
            ):
                return self._handle_change_credentials()

            # Show protected settings
            if "show" in query_lower and "protected" in query_lower:
                return self._show_protected_settings()

            # Default: show help
            return self._get_help()

        except Exception as e:
            return {"type": "error", "tool": "secure_settings", "error": str(e)}

    def _handle_setup_admin(self) -> dict:
        """Handle admin setup request."""
        if self.is_locked:
            return {
                "type": "error",
                "tool": "secure_settings",
                "message": "Admin access is already configured. Use 'change password' to update credentials.",
            }

        return {
            "type": "interactive_form",
            "tool": "secure_settings",
            "form": {
                "title": "Setup Admin Protection",
                "fields": [
                    {
                        "name": "pin",
                        "type": "password",
                        "label": "4-Digit PIN",
                        "required": True,
                        "pattern": "[0-9]{4}",
                        "placeholder": "Enter 4-digit PIN",
                    },
                    {
                        "name": "password",
                        "type": "password",
                        "label": "Admin Password",
                        "required": True,
                        "minlength": 8,
                        "placeholder": "Minimum 8 characters",
                    },
                    {
                        "name": "security_question",
                        "type": "select",
                        "label": "Security Question",
                        "options": [
                            "What was your first pet's name?",
                            "What city were you born in?",
                            "What is your mother's maiden name?",
                            "What was your first car?",
                            "What is your favorite book?",
                        ],
                        "required": True,
                    },
                    {
                        "name": "security_answer",
                        "type": "text",
                        "label": "Security Answer",
                        "required": True,
                        "placeholder": "Enter answer to security question",
                    },
                ],
            },
            "message": "⚠️ IMPORTANT: Remember these credentials! They protect critical system settings from unauthorized changes.",
        }

    def setup_admin(
        self, pin: str, password: str, security_question: str, security_answer: str
    ) -> bool:
        """Set up admin credentials."""
        if len(pin) != 4 or not pin.isdigit():
            return False

        if len(password) < 8:
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get salt
        cursor.execute("SELECT salt FROM admin_credentials WHERE id = 1")
        salt = cursor.fetchone()[0]

        # Hash credentials
        pin_hash = hashlib.pbkdf2_hmac(
            "sha256", pin.encode(), salt.encode(), 100000
        ).hex()
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100000
        ).hex()
        answer_hash = hashlib.pbkdf2_hmac(
            "sha256", security_answer.lower().encode(), salt.encode(), 100000
        ).hex()

        # Update credentials
        cursor.execute(
            """
            UPDATE admin_credentials 
            SET pin_hash = ?, password_hash = ?, security_question = ?, 
                security_answer_hash = ?, last_changed = ?
            WHERE id = 1
            """,
            (
                pin_hash,
                password_hash,
                security_question,
                answer_hash,
                datetime.now().isoformat(),
            ),
        )

        conn.commit()
        conn.close()

        self.is_locked = True
        self._log_access("admin_setup", None, True)

        return True

    def _handle_unlock(self) -> dict:
        """Handle unlock request."""
        if not self.is_locked:
            return {
                "type": "message",
                "tool": "secure_settings",
                "message": "Admin protection is not enabled. Use 'setup admin' to enable it.",
            }

        return {
            "type": "interactive_form",
            "tool": "secure_settings",
            "form": {
                "title": "Admin Authentication",
                "fields": [
                    {
                        "name": "auth_method",
                        "type": "select",
                        "label": "Authentication Method",
                        "options": ["PIN", "Password"],
                        "required": True,
                    },
                    {
                        "name": "credential",
                        "type": "password",
                        "label": "Enter Credential",
                        "required": True,
                    },
                ],
            },
            "message": "🔒 Enter admin credentials to unlock settings",
        }

    def authenticate(self, auth_method: str, credential: str) -> bool:
        """Authenticate admin access."""
        if not self.is_locked:
            return True

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT pin_hash, password_hash, salt FROM admin_credentials WHERE id = 1"
        )
        result = cursor.fetchone()
        conn.close()

        if not result:
            return False

        pin_hash, password_hash, salt = result

        # Hash provided credential
        credential_hash = hashlib.pbkdf2_hmac(
            "sha256", credential.encode(), salt.encode(), 100000
        ).hex()

        # Check based on method
        if auth_method.lower() == "pin" and credential_hash == pin_hash:
            self._log_access("authentication", None, True)
            return True
        elif auth_method.lower() == "password" and credential_hash == password_hash:
            self._log_access("authentication", None, True)
            return True

        self._log_access("authentication", None, False)
        return False

    def create_session_token(self) -> str:
        """Create a temporary admin session token."""
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO admin_sessions (token, expires_at) VALUES (?, ?)",
            (token, expires_at),
        )

        conn.commit()
        conn.close()

        return token

    def validate_session_token(self, token: str) -> bool:
        """Validate an admin session token."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT expires_at FROM admin_sessions WHERE token = ?", (token,)
        )

        result = cursor.fetchone()
        conn.close()

        if not result:
            return False

        expires_at = datetime.fromisoformat(result[0])
        return datetime.now() < expires_at

    def _get_lock_status(self) -> dict:
        """Get current lock status."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get protected settings count
        cursor.execute("SELECT COUNT(*) FROM protected_settings")
        protected_count = cursor.fetchone()[0]

        # Get recent access attempts
        cursor.execute(
            """
            SELECT action, success, timestamp FROM access_log
            ORDER BY timestamp DESC
            LIMIT 5
            """
        )
        recent_access = [
            {"action": action, "success": bool(success), "timestamp": ts}
            for action, success, ts in cursor.fetchall()
        ]

        conn.close()

        return {
            "type": "lock_status",
            "tool": "secure_settings",
            "locked": self.is_locked,
            "protected_settings_count": protected_count,
            "recent_access": recent_access,
            "message": (
                "🔒 Settings are protected"
                if self.is_locked
                else "⚠️ Settings are not protected"
            ),
        }

    def set_protected_setting(
        self,
        key: str,
        value: Any,
        category: str = "general",
        protection_level: str = "medium",
        token: Optional[str] = None,
    ) -> bool:
        """
        Set a protected setting. Requires valid admin token.
        """
        # Validate token if system is locked
        if self.is_locked and not (token and self.validate_session_token(token)):
            self._log_access("set_setting", key, False)
            return False

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Convert value to JSON string
        value_str = json.dumps(value)

        cursor.execute(
            """
            INSERT OR REPLACE INTO protected_settings 
            (key, value, category, protection_level, last_modified, modified_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                value_str,
                category,
                protection_level,
                datetime.now().isoformat(),
                "admin",
            ),
        )

        conn.commit()
        conn.close()

        self._log_access("set_setting", key, True)
        return True

    def get_protected_setting(
        self, key: str, token: Optional[str] = None
    ) -> Optional[Any]:
        """
        Get a protected setting. High protection settings require valid token.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT value, protection_level FROM protected_settings WHERE key = ?",
            (key,),
        )

        result = cursor.fetchone()
        conn.close()

        if not result:
            return None

        value_str, protection_level = result

        # High protection requires authentication
        if protection_level == "high" and self.is_locked:
            if not (token and self.validate_session_token(token)):
                self._log_access("get_setting", key, False)
                return None

        self._log_access("get_setting", key, True)
        return json.loads(value_str)

    def _show_protected_settings(self) -> dict:
        """Show list of protected settings (values hidden)."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT key, category, protection_level, last_modified
            FROM protected_settings
            ORDER BY category, key
            """
        )

        settings = []
        for key, category, protection_level, last_modified in cursor.fetchall():
            settings.append(
                {
                    "key": key,
                    "category": category,
                    "protection_level": protection_level,
                    "last_modified": last_modified,
                }
            )

        conn.close()

        return {
            "type": "protected_settings_list",
            "tool": "secure_settings",
            "settings": settings,
            "locked": self.is_locked,
        }

    def _log_access(
        self, action: str, setting_key: Optional[str], success: bool
    ) -> None:
        """Log an access attempt."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO access_log (action, setting_key, success) VALUES (?, ?, ?)",
            (action, setting_key, 1 if success else 0),
        )

        conn.commit()
        conn.close()

    def _handle_change_credentials(self) -> dict:
        """Handle credential change request."""
        if not self.is_locked:
            return {
                "type": "error",
                "tool": "secure_settings",
                "message": "Admin protection is not enabled. Use 'setup admin' first.",
            }

        return {
            "type": "interactive_form",
            "tool": "secure_settings",
            "form": {
                "title": "Change Admin Credentials",
                "fields": [
                    {
                        "name": "current_password",
                        "type": "password",
                        "label": "Current Password",
                        "required": True,
                    },
                    {
                        "name": "new_pin",
                        "type": "password",
                        "label": "New 4-Digit PIN",
                        "pattern": "[0-9]{4}",
                    },
                    {
                        "name": "new_password",
                        "type": "password",
                        "label": "New Password",
                        "minlength": 8,
                    },
                ],
            },
            "message": "Enter current password to change credentials",
        }

    def _get_help(self) -> dict:
        """Return help information."""
        return {
            "type": "settings_help",
            "tool": "secure_settings",
            "content": {
                "message": "Secure Settings - Protect critical configuration from unauthorized changes",
                "commands": [
                    "setup admin - Configure admin protection with PIN and password",
                    "status - Check if settings are locked",
                    "unlock - Authenticate to access protected settings",
                    "change password - Update admin credentials",
                    "show protected - List all protected settings",
                ],
                "features": [
                    "🔒 PIN and password protection",
                    "🛡️ Prevents unauthorized setting changes",
                    "👨‍👩‍👧 Parental control support",
                    "📝 Access logging and audit trail",
                    "⏱️ Temporary session tokens",
                    "🔐 Security question recovery",
                ],
                "locked": self.is_locked,
                "note": "Use this to prevent children or guests from changing critical AI behavior.",
            },
        }

    def execute(self, query: str) -> dict:
        """Execute method for reasoning engine."""
        return self.run(query)
