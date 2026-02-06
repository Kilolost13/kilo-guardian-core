from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from kilo_v2.models.auth_models import Base


class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    date = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat())
    amount = Column(Float, nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text)
    type = Column(String, nullable=False)  # 'expense' or 'income'
    account = Column(String, nullable=False)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())


class Budget(Base):
    __tablename__ = "budgets"
    category = Column(String, primary_key=True)
    monthly_limit = Column(Float, nullable=False)
    start_date = Column(String, nullable=False)


class FinancialGoal(Base):
    __tablename__ = "financial_goals"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    target_amount = Column(Float, nullable=False)
    current_amount = Column(Float, default=0)
    deadline = Column(String, nullable=False)
    priority = Column(String, default="medium")
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())


class GroceryList(Base):
    __tablename__ = "grocery_lists"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(String, default=lambda: datetime.utcnow().isoformat())
    completed = Column(Boolean, default=False)
    items = relationship("GroceryItem", back_populates="list")


class GroceryItem(Base):
    __tablename__ = "grocery_items"
    id = Column(Integer, primary_key=True)
    list_id = Column(Integer, ForeignKey("grocery_lists.id"), nullable=False)
    item_name = Column(String, nullable=False)
    quantity = Column(String)
    estimated_price = Column(Float)
    checked = Column(Boolean, default=False)
    list = relationship("GroceryList", back_populates="items")
