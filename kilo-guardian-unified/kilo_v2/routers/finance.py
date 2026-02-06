"""
Finance API Router - Expense tracking and budget management endpoints.

Provides endpoints for:
- Logging expenses from receipts
- Manual expense entry
- Budget tracking
- Financial summaries
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from kilo_v2.db import get_session
from kilo_v2.models.finance_models import Transaction

logger = logging.getLogger("FinanceRouter")

router = APIRouter()


class ExpenseLog(BaseModel):
    """Request model for logging an expense."""

    amount: float
    category: str
    vendor: Optional[str] = None
    date: Optional[str] = None  # ISO format, defaults to now
    notes: Optional[str] = None
    account: str = "default"


class ExpenseResponse(BaseModel):
    """Response model for expense logging."""

    success: bool
    transaction_id: int
    message: str
    total_spent_today: Optional[float] = None


@router.post("/finance/expenses/log", response_model=ExpenseResponse)
def log_expense(expense: ExpenseLog, db: Session = Depends(get_session)):
    """
    Log an expense to the spending tracker.

    This endpoint is used by the receipt scanner and manual entry.

    Args:
        expense: Expense data (amount, category, vendor, etc.)
        db: Database session

    Returns:
        Success confirmation with transaction ID
    """
    try:
        # Use current date if not provided
        expense_date = expense.date if expense.date else datetime.now().isoformat()

        # Create description
        description = expense.vendor if expense.vendor else "Expense"
        if expense.notes:
            description += f" - {expense.notes}"

        # Create transaction record
        transaction = Transaction(
            date=expense_date,
            amount=expense.amount,
            category=expense.category,
            description=description,
            type="expense",
            account=expense.account,
        )

        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        # Calculate total spent today (for confirmation message)
        today = datetime.now().date().isoformat()
        total_today = (
            db.query(Transaction)
            .filter(Transaction.date >= today, Transaction.type == "expense")
            .count()
        )

        logger.info(
            f"Logged expense: ${expense.amount:.2f} to {expense.category} (ID: {transaction.id})"
        )

        return ExpenseResponse(
            success=True,
            transaction_id=transaction.id,
            message=f"Logged ${expense.amount:.2f} to {expense.category}",
            total_spent_today=None,  # Could calculate sum if needed
        )

    except Exception as e:
        logger.error(f"Error logging expense: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/finance/expenses/today", response_model=List[dict])
def get_today_expenses(db: Session = Depends(get_session)):
    """
    Get all expenses logged today.

    Returns:
        List of expense transactions
    """
    try:
        today = datetime.now().date().isoformat()

        transactions = (
            db.query(Transaction)
            .filter(Transaction.date >= today, Transaction.type == "expense")
            .order_by(Transaction.created_at.desc())
            .all()
        )

        results = [
            {
                "id": t.id,
                "amount": t.amount,
                "category": t.category,
                "description": t.description,
                "date": t.date,
                "created_at": t.created_at,
            }
            for t in transactions
        ]

        return results

    except Exception as e:
        logger.error(f"Error fetching today's expenses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/finance/summary", response_model=dict)
def get_finance_summary(db: Session = Depends(get_session)):
    """
    Get financial summary (total spent, by category, etc.).

    Returns:
        Financial summary data
    """
    try:
        # Get today's date
        today = datetime.now().date().isoformat()

        # Total spent today
        today_transactions = (
            db.query(Transaction)
            .filter(Transaction.date >= today, Transaction.type == "expense")
            .all()
        )

        total_today = sum(t.amount for t in today_transactions)

        # Spending by category (last 30 days)
        from datetime import timedelta

        thirty_days_ago = (datetime.now() - timedelta(days=30)).date().isoformat()

        recent_transactions = (
            db.query(Transaction)
            .filter(Transaction.date >= thirty_days_ago, Transaction.type == "expense")
            .all()
        )

        # Group by category
        by_category = {}
        for t in recent_transactions:
            category = t.category or "Other"
            by_category[category] = by_category.get(category, 0) + t.amount

        # Format recent transactions for frontend
        recent_tx_list = [
            {
                "id": t.id,
                "date": t.date,
                "description": t.description,
                "amount": t.amount,
                "category": t.category,
            }
            for t in recent_transactions[:10]  # Last 10 transactions
        ]

        return {
            "total_today": total_today,
            "transactions_today": len(today_transactions),
            "spending_by_category": by_category,
            "recent_transactions": recent_tx_list,
            "period": "30 days",
        }

    except Exception as e:
        logger.error(f"Error generating finance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
