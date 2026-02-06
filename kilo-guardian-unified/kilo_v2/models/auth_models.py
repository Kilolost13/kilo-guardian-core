from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False, unique=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    email_verified = Column(Boolean, default=False)
    stripe_customer_id = Column(String)
    subscription_tier = Column(String, default="free")
    subscription_status = Column(String, default="inactive")
    sessions = relationship("Session", back_populates="user")


class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String, nullable=False, unique=True)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    expires_at = Column(String)
    ip_address = Column(String)
    user_agent = Column(String)
    user = relationship("User", back_populates="sessions")


class Appliance(Base):
    __tablename__ = "appliances"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    hardware_id = Column(String, nullable=False, unique=True)
    device_name = Column(String)
    registered_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    last_seen = Column(String)
    is_active = Column(Boolean, default=True)


class Purchase(Base):
    __tablename__ = "purchases"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    item_type = Column(String, nullable=False)
    item_id = Column(String, nullable=False)
    amount = Column(Numeric(10, 2))
    stripe_payment_id = Column(String)
    purchased_at = Column(String, default=lambda: datetime.utcnow().isoformat())
