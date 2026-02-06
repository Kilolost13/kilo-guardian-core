"""
User Authentication System for Bastion AI
Handles user registration, login, sessions, and appliance linking
"""

import hashlib
import logging
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from kilo_v2.db import get_session
from kilo_v2.models.auth_models import Appliance, Purchase
from kilo_v2.models.auth_models import Session as UserSession
from kilo_v2.models.auth_models import User

logger = logging.getLogger(__name__)

from kilo_v2.db import get_engine


class AuthManager:
    """Manages user authentication and sessions"""

    def __init__(self, db_path: str = None):
        # Enforce use of SQLAlchemy (database URL required) - avoid sqlite fallback
        self.db_path = db_path
        # Keep sqlite init for backwards compatibility; also create SQLAlchemy metadata if necessary
        self._init_database()
        # Create SQLAlchemy tables if running against sqlite (local dev)
        try:
            from kilo_v2.db import get_engine
            from kilo_v2.models.auth_models import Base as AuthBase

            engine = get_engine()
            AuthBase.metadata.create_all(bind=engine)
        except Exception:
            pass

    def _init_database(self):
        """Initialize database with required tables"""
        # Only initialize sqlite tables if db_path is explicitly provided
        if not self.db_path:
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Users table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                email_verified BOOLEAN DEFAULT 0,
                stripe_customer_id TEXT,
                subscription_tier TEXT DEFAULT 'free',
                subscription_status TEXT DEFAULT 'inactive'
            )
        """
        )

        # Sessions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Appliances table (links hardware to users)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS appliances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                hardware_id TEXT UNIQUE NOT NULL,
                device_name TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        # Purchases table (marketplace transactions)
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_id TEXT NOT NULL,
                amount DECIMAL(10, 2),
                stripe_payment_id TEXT,
                purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """
        )

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(32)

        pwd_hash = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
        )
        return pwd_hash.hex(), salt

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash"""
        # Hash format: salt$hash
        if "$" not in stored_hash:
            return False

        salt, hash_value = stored_hash.split("$")
        pwd_hash, _ = self._hash_password(password, salt)
        return pwd_hash == hash_value

    def create_user(
        self,
        email: str,
        password: str,
        full_name: str = None,
        stripe_customer_id: str = None,
    ) -> Dict[str, Any]:
        """Create a new user with SQLAlchemy where possible, fall back to sqlite otherwise"""
        # Try SQLAlchemy path
        try:
            s: Session = get_session()
            if s:
                existing = s.query(User).filter(User.email == email).first()
                if existing:
                    s.close()
                    return {"success": False, "error": "Email already registered"}
                pwd_hash, salt = self._hash_password(password)
                stored_hash = f"{salt}${pwd_hash}"
                u = User(
                    email=email,
                    password_hash=stored_hash,
                    full_name=full_name,
                    stripe_customer_id=stripe_customer_id,
                )
                s.add(u)
                s.commit()
                # Access attributes before closing session to avoid DetachedInstanceError
                user_id = u.id
                user_email = u.email
                user_full_name = u.full_name
                s.close()
                logger.info(f"Created user: {email} (ID: {user_id})")
                return {
                    "success": True,
                    "user_id": user_id,
                    "email": user_email,
                    "full_name": user_full_name,
                }
        except SAIntegrityError as e:
            logger.warning(f"SQLAlchemy Integrity error creating user: {e}")
            return {"success": False, "error": "Email already registered"}
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemy error creating user: {e}")
        except Exception as e:
            logger.error(f"Error creating user (session path): {e}")

        # Do not provide sqlite fallback; require SQLAlchemy engine
        try:
            s = get_session()
            if not s:
                raise RuntimeError(
                    "Database session unavailable; configure DATABASE_URL to a valid DB."
                )
        except Exception as e:
            logger.exception(f"No database session available: {e}")
            return {"success": False, "error": "Database unavailable"}

    def authenticate(
        self, email: str, password: str, ip_address: str = None, user_agent: str = None
    ) -> Dict[str, Any]:
        """
        Authenticate user and create session.

        Returns:
            dict with session token and user info, or error
        """
        # First try SQLAlchemy-based session if available
        try:
            s = get_session()
            if s:
                user = s.query(User).filter(User.email == email).first()
                if not user:
                    s.close()
                    return {"success": False, "error": "Invalid credentials"}
                if not self._verify_password(password, user.password_hash):
                    s.close()
                    return {"success": False, "error": "Invalid credentials"}

                # Create session token
                session_token = secrets.token_urlsafe(32)
                expires_at = (datetime.now() + timedelta(days=30)).isoformat()
                sess = UserSession(
                    user_id=user.id,
                    session_token=session_token,
                    expires_at=expires_at,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                s.add(sess)
                s.commit()
                s_id = sess.id if hasattr(sess, "id") else None
                # Query user attributes before closing
                user_id = user.id
                user_email = user.email
                user_full_name = user.full_name
                user_subscription_tier = user.subscription_tier
                user_subscription_status = user.subscription_status
                s.close()

                logger.info(f"User logged in: {email}")
                return {
                    "success": True,
                    "session_token": session_token,
                    "user": {
                        "id": user_id,
                        "email": user_email,
                        "full_name": user_full_name,
                        "subscription_tier": user_subscription_tier,
                        "subscription_status": user_subscription_status,
                    },
                }
        except Exception as e:
            logger.exception(f"SQLAlchemy auth path failed: {e}")

        # No sqlite fallback - SQLAlchemy path already attempted above. If we reach here, report failure
        return {
            "success": False,
            "error": "Database path not available for authentication",
        }

    def verify_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Verify session token and return user info if valid.

        Returns:
            User dict or None if invalid/expired
        """
        # Try SQLAlchemy path first
        try:
            s = get_session()
            if s:
                res = (
                    s.query(
                        User.id,
                        User.email,
                        User.full_name,
                        User.subscription_tier,
                        User.subscription_status,
                        UserSession.expires_at,
                    )
                    .join(UserSession, User.id == UserSession.user_id)
                    .filter(UserSession.session_token == session_token)
                    .first()
                )
                s.close()
                if not res:
                    return None
                user_id, email, full_name, sub_tier, sub_status, expires_at = res
                expires = datetime.fromisoformat(expires_at)
                if expires < datetime.now():
                    return None
                return {
                    "id": user_id,
                    "email": email,
                    "full_name": full_name,
                    "subscription_tier": sub_tier,
                    "subscription_status": sub_status,
                }
        except Exception as e:
            logger.exception(f"SQLAlchemy verify session failed: {e}")

        # No sqlite fallback; SQLAlchemy attempted above
        return None

    def logout(self, session_token: str) -> bool:
        """Delete session (logout)"""
        try:
            s = get_session()
            if s:
                s.query(UserSession).filter(
                    UserSession.session_token == session_token
                ).delete()
                s.commit()
                s.close()
                return True
        except Exception as e:
            logger.exception(f"SQLAlchemy logout failed: {e}")

        # No sqlite fallback
        return False

    def link_appliance(
        self, user_id: int, hardware_id: str, device_name: str = None
    ) -> bool:
        """Link an appliance to a user account"""
        try:
            s = get_session()
            if s:
                a = Appliance(
                    user_id=user_id, hardware_id=hardware_id, device_name=device_name
                )
                s.add(a)
                s.commit()
                s.close()
                logger.info(f"Linked appliance {hardware_id} to user {user_id}")
                return True
        except SAIntegrityError:
            logger.warning(f"Appliance {hardware_id} already linked (SQLAlchemy)")
            return False
        except Exception as e:
            logger.exception(f"SQLAlchemy link appliance failed: {e}")

        # No sqlite fallback path allowed
        return False

    def get_user_appliances(self, user_id: int) -> list:
        """Get all appliances for a user"""
        try:
            s = get_session()
            if s:
                rows = (
                    s.query(Appliance)
                    .filter(Appliance.user_id == user_id)
                    .order_by(Appliance.registered_at.desc())
                    .all()
                )
                appliances = [
                    {
                        "hardware_id": r.hardware_id,
                        "device_name": r.device_name,
                        "registered_at": r.registered_at,
                        "last_seen": r.last_seen,
                        "is_active": bool(r.is_active),
                    }
                    for r in rows
                ]
                s.close()
                return appliances
        except Exception as e:
            logger.exception(f"SQLAlchemy fetch appliances failed: {e}")

        # No sqlite fallback
        return []

    def update_subscription(self, user_id: int, tier: str, status: str) -> bool:
        """Update user subscription tier and status"""
        try:
            s = get_session()
            if s:
                user = s.query(User).filter(User.id == user_id).first()
                if not user:
                    s.close()
                    return False
                user.subscription_tier = tier
                user.subscription_status = status
                s.commit()
                s.close()
                logger.info(
                    f"Updated subscription for user {user_id}: {tier} - {status}"
                )
                return True
        except Exception as e:
            logger.exception(f"SQLAlchemy update subscription failed: {e}")

        # No sqlite fallback
        return False

    def record_purchase(
        self,
        user_id: int,
        item_type: str,
        item_id: str,
        amount: float,
        stripe_payment_id: str = None,
    ) -> bool:
        """Record a marketplace purchase"""
        try:
            s = get_session()
            if s:
                p = Purchase(
                    user_id=user_id,
                    item_type=item_type,
                    item_id=item_id,
                    amount=amount,
                    stripe_payment_id=stripe_payment_id,
                )
                s.add(p)
                s.commit()
                s.close()
                logger.info(
                    f"Recorded purchase: User {user_id} bought {item_type} {item_id}"
                )
                return True
        except Exception as e:
            logger.exception(f"SQLAlchemy record purchase failed: {e}")

        # No sqlite fallback
        return False

    def get_user_purchases(self, user_id: int) -> list:
        """Get all purchases for a user"""
        try:
            s = get_session()
            if s:
                rows = (
                    s.query(Purchase)
                    .filter(Purchase.user_id == user_id)
                    .order_by(Purchase.purchased_at.desc())
                    .all()
                )
                purchases = [
                    {
                        "item_type": r.item_type,
                        "item_id": r.item_id,
                        "amount": float(r.amount),
                        "purchased_at": r.purchased_at,
                    }
                    for r in rows
                ]
                s.close()
                return purchases
        except Exception as e:
            logger.exception(f"SQLAlchemy fetch purchases failed: {e}")

        # No sqlite fallback
        return []


# Global instance
auth_manager = AuthManager()
