"""
Finance Manager Plugin for Kilo Guardian
Tracks spending habits, budgets, grocery lists, and financial goals.
"""

import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from plugins.base_plugin import BasePlugin
from sqlalchemy import func

from kilo_v2.config import FORCE_SQL_ALCHEMY
from kilo_v2.db import get_engine, get_session
from kilo_v2.models.auth_models import Base
from kilo_v2.models.finance_models import Budget as BudgetModel
from kilo_v2.models.finance_models import FinancialGoal as FinancialGoalModel
from kilo_v2.models.finance_models import GroceryItem as GroceryItemModel
from kilo_v2.models.finance_models import GroceryList as GroceryListModel
from kilo_v2.models.finance_models import Transaction as TransactionModel


@dataclass
class Transaction:
    """Represents a financial transaction."""

    id: Optional[int]
    date: str
    amount: float
    category: str
    description: str
    type: str  # 'expense' or 'income'
    account: str

    def to_dict(self):
        return asdict(self)


@dataclass
class Budget:
    """Represents a budget for a category."""

    category: str
    monthly_limit: float
    current_spent: float
    start_date: str

    def remaining(self) -> float:
        return self.monthly_limit - self.current_spent

    def percentage_used(self) -> float:
        if self.monthly_limit == 0:
            return 0
        return (self.current_spent / self.monthly_limit) * 100


@dataclass
class FinancialGoal:
    """Represents a financial goal."""

    id: Optional[int]
    name: str
    target_amount: float
    current_amount: float
    deadline: str
    priority: str  # 'high', 'medium', 'low'

    def progress_percentage(self) -> float:
        if self.target_amount == 0:
            return 0
        return (self.current_amount / self.target_amount) * 100

    def remaining_amount(self) -> float:
        return self.target_amount - self.current_amount

    def days_remaining(self) -> int:
        deadline_date = datetime.fromisoformat(self.deadline)
        today = datetime.now()
        return (deadline_date - today).days


class FinanceManager(BasePlugin):
    def format_spending_analysis(self, analysis: dict) -> str:
        """Format the spending analysis as readable text."""
        lines = []
        lines.append("\n=== Spending Analysis ===\n")
        lines.append(f"Period: {analysis.get('period', 'N/A')}")
        lines.append("\nCategory Breakdown:")
        cb = analysis.get("category_breakdown", [])
        if cb:
            for c in cb:
                lines.append(
                    f"  - {c.get('category', 'Unknown')}: ${c.get('total', 0):,.2f} ({c.get('transactions', 0)} txns)"
                )
        else:
            lines.append("  No category data.")
        lines.append("\nMonthly Trend:")
        mt = analysis.get("monthly_trend", [])
        if mt:
            for m in mt:
                lines.append(f"  - {m.get('month', 'N/A')}: ${m.get('total', 0):,.2f}")
        else:
            lines.append("  No monthly data.")
        lines.append(
            f"\nAverage Transaction: ${analysis.get('average_transaction', 0):,.2f}"
        )
        lines.append("\nPatterns:")
        patterns = analysis.get("patterns", [])
        if patterns:
            for p in patterns:
                lines.append(f"  - {p}")
        else:
            lines.append("  No patterns detected.")
        lines.append("\nInsights:")
        insights = analysis.get("insights", [])
        if insights:
            for i in insights:
                lines.append(f"  - {i}")
        else:
            lines.append("  No insights.")
        return "\n".join(lines)

    def format_spending_summary(self, summary: dict) -> str:
        """Format the spending summary as readable text."""
        lines = []
        lines.append("\n=== Spending Summary ===\n")
        lines.append(f"Period: {summary.get('period', 'N/A')}")
        lines.append(f"Total Income: ${summary.get('total_income', 0):,.2f}")
        lines.append(f"Total Expenses: ${summary.get('total_expenses', 0):,.2f}")
        lines.append(f"Net: ${summary.get('net', 0):,.2f}")
        status = summary.get("status", "").capitalize()
        lines.append(f"Status: {status if status else 'N/A'}")
        top_expenses = summary.get("top_expenses", [])
        if top_expenses:
            lines.append("Top Expenses:")
            for e in top_expenses:
                lines.append(
                    f"  - {e.get('category', 'Unknown')}: ${e.get('amount', 0):,.2f}"
                )
        else:
            lines.append("Top Expenses: None")
        return "\n".join(lines)

    def format_financial_overview(self, overview: dict) -> str:
        """Format the financial overview as readable text."""
        sections = overview.get("sections", {})
        spending = sections.get("spending", {})
        budgets = sections.get("budgets", {})
        goals = sections.get("goals", {})

        lines = []
        lines.append("\n=== Financial Overview ===\n")
        # Spending Summary
        lines.append("Spending Summary:")
        lines.append(f"  Period: {spending.get('period', 'N/A')}")
        lines.append(f"  Total Income: ${spending.get('total_income', 0):,.2f}")
        lines.append(f"  Total Expenses: ${spending.get('total_expenses', 0):,.2f}")
        lines.append(f"  Net: ${spending.get('net', 0):,.2f}")
        status = spending.get("status", "").capitalize()
        lines.append(f"  Status: {status if status else 'N/A'}")
        top_expenses = spending.get("top_expenses", [])
        if top_expenses:
            lines.append("  Top Expenses:")
            for e in top_expenses:
                lines.append(
                    f"    - {e.get('category', 'Unknown')}: ${e.get('amount', 0):,.2f}"
                )
        else:
            lines.append("  Top Expenses: None")
        # Budgets
        lines.append("\nBudgets:")
        budget_list = budgets.get("budgets", [])
        if budget_list:
            for b in budget_list:
                lines.append(
                    f"  - {b.get('category', 'Unknown')}: Limit ${b.get('limit', 0):,.2f}, Spent ${b.get('spent', 0):,.2f}, Remaining ${b.get('remaining', 0):,.2f}"
                )
        else:
            lines.append("  No budgets defined.")
        summary = budgets.get("summary", {})
        lines.append(f"  Total Budgeted: ${summary.get('total_budgeted', 0):,.2f}")
        lines.append(f"  Total Spent: ${summary.get('total_spent', 0):,.2f}")
        lines.append(
            f"  Categories Over Budget: {summary.get('categories_over_budget', 0)}"
        )
        # Goals
        lines.append("\nGoals:")
        goals_list = goals.get("goals", [])
        if goals_list:
            for g in goals_list:
                lines.append(
                    f"  - {g.get('name', 'Unnamed')}: ${g.get('current_amount', 0):,.2f}/${g.get('target_amount', 0):,.2f} ({g.get('progress', 0):.1f}%), Deadline: {g.get('deadline', 'N/A')}, Priority: {g.get('priority', 'N/A')}"
                )
        else:
            lines.append("  No goals defined.")
        lines.append(f"  Total Goals: {goals.get('total_goals', 0)}")
        lines.append(f"  Active Goals: {goals.get('active_goals', 0)}")
        return "\n".join(lines)

    def format_spending_summary(self, summary: dict) -> str:
        """Format the spending summary as readable text."""
        lines = []
        lines.append("\n=== Spending Summary ===\n")
        lines.append(f"Period: {summary.get('period', 'N/A')}")
        lines.append(f"Total Income: ${summary.get('total_income', 0):,.2f}")
        lines.append(f"Total Expenses: ${summary.get('total_expenses', 0):,.2f}")
        lines.append(f"Net: ${summary.get('net', 0):,.2f}")
        status = summary.get("status", "").capitalize()
        lines.append(f"Status: {status if status else 'N/A'}")
        top_expenses = summary.get("top_expenses", [])
        if top_expenses:
            lines.append("Top Expenses:")
            for e in top_expenses:
                lines.append(
                    f"  - {e.get('category', 'Unknown')}: ${e.get('amount', 0):,.2f}"
                )
        else:
            lines.append("Top Expenses: None")
        return "\n".join(lines)

    def format_financial_overview(self, overview: dict) -> str:
        """Format the financial overview as readable text."""
        sections = overview.get("sections", {})
        spending = sections.get("spending", {})
        budgets = sections.get("budgets", {})
        goals = sections.get("goals", {})

        lines = []
        lines.append("\n=== Financial Overview ===\n")
        # Spending Summary
        lines.append("Spending Summary:")
        lines.append(f"  Period: {spending.get('period', 'N/A')}")
        lines.append(f"  Total Income: ${spending.get('total_income', 0):,.2f}")
        lines.append(f"  Total Expenses: ${spending.get('total_expenses', 0):,.2f}")
        lines.append(f"  Net: ${spending.get('net', 0):,.2f}")
        status = spending.get("status", "").capitalize()
        lines.append(f"  Status: {status if status else 'N/A'}")
        top_expenses = spending.get("top_expenses", [])
        if top_expenses:
            lines.append("  Top Expenses:")
            for e in top_expenses:
                lines.append(
                    f"    - {e.get('category', 'Unknown')}: ${e.get('amount', 0):,.2f}"
                )
        else:
            lines.append("  Top Expenses: None")

        # Budgets
        lines.append("\nBudgets:")
        budget_list = budgets.get("budgets", [])
        if budget_list:
            for b in budget_list:
                lines.append(
                    f"  - {b.get('category', 'Unknown')}: Limit ${b.get('limit', 0):,.2f}, Spent ${b.get('spent', 0):,.2f}, Remaining ${b.get('remaining', 0):,.2f}"
                )
        else:
            lines.append("  No budgets defined.")
        summary = budgets.get("summary", {})
        lines.append(f"  Total Budgeted: ${summary.get('total_budgeted', 0):,.2f}")
        lines.append(f"  Total Spent: ${summary.get('total_spent', 0):,.2f}")
        lines.append(
            f"  Categories Over Budget: {summary.get('categories_over_budget', 0)}"
        )

        # Goals
        lines.append("\nGoals:")
        goals_list = goals.get("goals", [])
        if goals_list:
            for g in goals_list:
                lines.append(
                    f"  - {g.get('name', 'Unnamed')}: ${g.get('current_amount', 0):,.2f}/${g.get('target_amount', 0):,.2f} ({g.get('progress', 0):.1f}%), Deadline: {g.get('deadline', 'N/A')}, Priority: {g.get('priority', 'N/A')}"
                )
        else:
            lines.append("  No goals defined.")
        lines.append(f"  Total Goals: {goals.get('total_goals', 0)}")
        lines.append(f"  Active Goals: {goals.get('active_goals', 0)}")

        return "\n".join(lines)

    """
    Financial management plugin for Kilo Guardian.
    Provides budget tracking, spending analysis, and financial goal management.
    """

    def __init__(self):
        super().__init__()
        # keep path around for backward compatibility or export/import
        self.db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "user_data", "finance.db"
        )
        self._init_database()

    def _init_database(self):
        """Initialize the finance database."""
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # Prefer SQLAlchemy-backed storage where configured
        engine = get_engine()
        if FORCE_SQL_ALCHEMY:
            Base.metadata.create_all(engine)
            return

        # Fallback to legacy sqlite if not enforcing SQLAlchemy
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Transactions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                type TEXT NOT NULL,
                account TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Budgets table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS budgets (
                category TEXT PRIMARY KEY,
                monthly_limit REAL NOT NULL,
                start_date TEXT NOT NULL
            )
        """
        )

        # Financial goals table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS financial_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_amount REAL NOT NULL,
                current_amount REAL DEFAULT 0,
                deadline TEXT NOT NULL,
                priority TEXT DEFAULT 'medium',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Grocery lists table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS grocery_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                completed INTEGER DEFAULT 0
            )
        """
        )

        # Grocery items table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS grocery_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                quantity TEXT,
                estimated_price REAL,
                checked INTEGER DEFAULT 0,
                FOREIGN KEY (list_id) REFERENCES grocery_lists(id)
            )
        """
        )

        conn.commit()
        conn.close()

    def get_name(self) -> str:
        return "finance_manager"

    def get_keywords(self) -> list:
        return [
            "money",
            "budget",
            "spending",
            "expense",
            "income",
            "finance",
            "financial",
            "transaction",
            "bank",
            "banking",
            "savings",
            "save",
            "goal",
            "grocery",
            "groceries",
            "shopping",
            "list",
            "bill",
            "bills",
            "payment",
            "cost",
        ]

    def run(self, query: str):
        """Main execution method for finance queries."""
        query_lower = query.lower()
        try:
            # Transaction tracking
            if "add transaction" in query_lower or "record expense" in query_lower:
                return self._handle_add_transaction(query)

            # Budget management
            if "set budget" in query_lower or "create budget" in query_lower:
                return self._handle_set_budget(query)

            if "budget" in query_lower and (
                "status" in query_lower or "check" in query_lower
            ):
                return self._get_budget_status()

            # Spending analysis
            if "spending" in query_lower and (
                "habit" in query_lower or "analysis" in query_lower
            ):
                return self._analyze_spending_habits()

            if "spending" in query_lower and "summary" in query_lower:
                return self._get_spending_summary()

            # Financial goals
            if (
                "add goal" in query_lower
                or "create goal" in query_lower
                or "set goal" in query_lower
            ):
                return self._handle_add_goal(query)

            if "goal" in query_lower and (
                "status" in query_lower or "progress" in query_lower
            ):
                return self._get_goals_status()

            # Grocery lists
            if "grocery" in query_lower and (
                "list" in query_lower or "create" in query_lower
            ):
                return self._handle_grocery_list(query)

            if "grocery" in query_lower and "show" in query_lower:
                return self._show_grocery_lists()

            # Financial advice
            if (
                "advice" in query_lower
                or "suggestion" in query_lower
                or "recommend" in query_lower
            ):
                return self._provide_financial_advice()

            # Default overview: return formatted text
            overview = self._get_financial_overview()
            return {
                "type": "formatted_text",
                "tool": "finance_manager",
                "content": self.format_financial_overview(overview),
            }

        except Exception as e:
            return {"type": "error", "tool": "finance_manager", "error": str(e)}

    def _handle_add_transaction(self, query: str) -> dict:
        """Parse and add a transaction from natural language."""
        # This is a simplified parser - in production, use NLP or structured input
        return {
            "type": "interactive_form",
            "tool": "finance_manager",
            "form": {
                "title": "Add Transaction",
                "fields": [
                    {
                        "name": "amount",
                        "type": "number",
                        "label": "Amount",
                        "required": True,
                    },
                    {
                        "name": "category",
                        "type": "select",
                        "label": "Category",
                        "options": [
                            "Groceries",
                            "Utilities",
                            "Entertainment",
                            "Transportation",
                            "Healthcare",
                            "Dining",
                            "Shopping",
                            "Other",
                        ],
                    },
                    {"name": "description", "type": "text", "label": "Description"},
                    {
                        "name": "type",
                        "type": "select",
                        "label": "Type",
                        "options": ["expense", "income"],
                    },
                    {
                        "name": "account",
                        "type": "text",
                        "label": "Account",
                        "default": "primary",
                    },
                ],
            },
            "message": "Please provide transaction details",
        }

    def add_transaction(
        self,
        amount: float,
        category: str,
        description: str,
        transaction_type: str = "expense",
        account: str = "primary",
    ) -> bool:
        """Add a transaction to the database."""
        session = get_session()

        tx = TransactionModel(
            date=datetime.now().isoformat(),
            amount=amount,
            category=category,
            description=description,
            type=transaction_type,
            account=account,
        )
        session.add(tx)
        session.commit()
        session.close()
        return True

    def _handle_set_budget(self, query: str) -> dict:
        """Handle budget setting request."""
        return {
            "type": "interactive_form",
            "tool": "finance_manager",
            "form": {
                "title": "Set Monthly Budget",
                "fields": [
                    {
                        "name": "category",
                        "type": "select",
                        "label": "Category",
                        "options": [
                            "Groceries",
                            "Utilities",
                            "Entertainment",
                            "Transportation",
                            "Healthcare",
                            "Dining",
                            "Shopping",
                            "Other",
                        ],
                    },
                    {
                        "name": "monthly_limit",
                        "type": "number",
                        "label": "Monthly Limit ($)",
                        "required": True,
                    },
                ],
            },
            "message": "Set a budget limit for a spending category",
        }

    def set_budget(self, category: str, monthly_limit: float) -> bool:
        """Set or update a budget for a category."""
        session = get_session()

        existing = session.get(BudgetModel, category)
        if existing:
            existing.monthly_limit = monthly_limit
            existing.start_date = datetime.now().isoformat()
        else:
            b = BudgetModel(
                category=category,
                monthly_limit=monthly_limit,
                start_date=datetime.now().isoformat(),
            )
            session.add(b)
        session.commit()
        session.close()
        return True

    def _get_budget_status(self) -> dict:
        """Get current budget status for all categories."""
        session = get_session()

        # Get all budgets
        budgets = session.query(BudgetModel).all()

        budget_status = []
        current_month = datetime.now().strftime("%Y-%m")

        for budget_obj in budgets:
            category = budget_obj.category
            monthly_limit = budget_obj.monthly_limit
            start_date = budget_obj.start_date

            # Calculate current month's spending
            current_spent = (
                session.query(func.coalesce(func.sum(TransactionModel.amount), 0.0))
                .filter(
                    TransactionModel.category == category,
                    TransactionModel.type == "expense",
                    TransactionModel.date.like(f"{current_month}%"),
                )
                .scalar()
                or 0.0
            )

            budget = Budget(
                category=category,
                monthly_limit=monthly_limit,
                current_spent=current_spent,
                start_date=start_date,
            )

            budget_status.append(
                {
                    "category": category,
                    "limit": monthly_limit,
                    "spent": current_spent,
                    "remaining": budget.remaining(),
                    "percentage": budget.percentage_used(),
                    "status": (
                        "over"
                        if budget.remaining() < 0
                        else "warning" if budget.percentage_used() > 80 else "good"
                    ),
                }
            )

        session.close()

        return {
            "type": "budget_status",
            "tool": "finance_manager",
            "budgets": budget_status,
            "summary": {
                "total_budgeted": sum(b["limit"] for b in budget_status),
                "total_spent": sum(b["spent"] for b in budget_status),
                "categories_over_budget": len(
                    [b for b in budget_status if b["status"] == "over"]
                ),
            },
        }

    def _analyze_spending_habits(self):
        """Analyze spending patterns over the last 3 months."""
        if FORCE_SQL_ALCHEMY:
            session = get_session()
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

        # Get last 3 months of data
        three_months_ago = (datetime.now() - timedelta(days=90)).isoformat()

        # Spending by category
        if FORCE_SQL_ALCHEMY:
            # aggregate by category
            rows = (
                session.query(
                    TransactionModel.category,
                    func.coalesce(func.sum(TransactionModel.amount), 0.0).label(
                        "total"
                    ),
                    func.count(TransactionModel.id).label("count"),
                )
                .filter(
                    TransactionModel.type == "expense",
                    TransactionModel.date >= three_months_ago,
                )
                .group_by(TransactionModel.category)
                .order_by(func.sum(TransactionModel.amount).desc())
                .all()
            )
            category_spending = [
                {"category": r[0], "total": r[1], "transactions": r[2]} for r in rows
            ]
        else:
            cursor.execute(
                """
                SELECT category, SUM(amount), COUNT(*) 
                FROM transactions
                WHERE type = 'expense' AND date >= ?
                GROUP BY category
                ORDER BY SUM(amount) DESC
            """,
                (three_months_ago,),
            )

            category_spending = [
                {"category": cat, "total": total, "transactions": count}
                for cat, total, count in cursor.fetchall()
            ]

        # Monthly trend
        if FORCE_SQL_ALCHEMY:
            # Retrieve all expense txs since three_months_ago and bucket by month in Python
            rows = (
                session.query(TransactionModel.date, TransactionModel.amount)
                .filter(
                    TransactionModel.type == "expense",
                    TransactionModel.date >= three_months_ago,
                )
                .order_by(TransactionModel.date)
                .all()
            )
            monthly_sums = {}
            for date_str, amt in rows:
                month_key = date_str[:7]
                monthly_sums.setdefault(month_key, 0.0)
                monthly_sums[month_key] += amt
            monthly_trend = [
                {"month": m, "total": monthly_sums[m]}
                for m in sorted(monthly_sums.keys())
            ]
        else:
            cursor.execute(
                """
                SELECT strftime('%Y-%m', date) as month, SUM(amount)
                FROM transactions
                WHERE type = 'expense' AND date >= ?
                GROUP BY month
                ORDER BY month
            """,
                (three_months_ago,),
            )

            monthly_trend = [
                {"month": month, "total": total} for month, total in cursor.fetchall()
            ]

        # Average transaction size
        if FORCE_SQL_ALCHEMY:
            avg_transaction = (
                session.query(func.avg(TransactionModel.amount))
                .filter(
                    TransactionModel.type == "expense",
                    TransactionModel.date >= three_months_ago,
                )
                .scalar()
                or 0
            )
        else:
            cursor.execute(
                """
                SELECT AVG(amount) FROM transactions
                WHERE type = 'expense' AND date >= ?
            """,
                (three_months_ago,),
            )

            avg_transaction = cursor.fetchone()[0] or 0

        # Identify patterns
        patterns = self._identify_patterns(category_spending, monthly_trend)

        if FORCE_SQL_ALCHEMY:
            session.close()
        else:
            conn.close()

        analysis = {
            "type": "spending_analysis",
            "tool": "finance_manager",
            "period": "Last 3 months",
            "category_breakdown": category_spending,
            "monthly_trend": monthly_trend,
            "average_transaction": round(avg_transaction, 2),
            "patterns": patterns,
            "insights": self._generate_insights(category_spending, monthly_trend),
        }
        return {
            "type": "formatted_text",
            "tool": "finance_manager",
            "content": self.format_spending_analysis(analysis),
        }

    def _identify_patterns(
        self, category_spending: List[dict], monthly_trend: List[dict]
    ) -> List[str]:
        """Identify spending patterns."""
        patterns = []

        if len(category_spending) > 0:
            top_category = category_spending[0]
            patterns.append(
                f"Your highest spending category is {top_category['category']} (${top_category['total']:.2f})"
            )

        if len(monthly_trend) >= 2:
            recent_total = monthly_trend[-1]["total"]
            previous_total = monthly_trend[-2]["total"]
            change = ((recent_total - previous_total) / previous_total) * 100

            if abs(change) > 10:
                direction = "increased" if change > 0 else "decreased"
                patterns.append(
                    f"Your spending {direction} by {abs(change):.1f}% last month"
                )

        return patterns

    def _generate_insights(
        self, category_spending: List[dict], monthly_trend: List[dict]
    ) -> List[str]:
        """Generate actionable insights."""
        insights = []

        # High spending categories
        if len(category_spending) > 0:
            top_three = category_spending[:3]
            total_top_three = sum(c["total"] for c in top_three)
            insights.append(
                f"Your top 3 categories account for ${total_top_three:.2f} of spending"
            )

        # Trend analysis
        if len(monthly_trend) >= 3:
            recent_avg = sum(m["total"] for m in monthly_trend[-2:]) / 2
            overall_avg = sum(m["total"] for m in monthly_trend) / len(monthly_trend)

            if recent_avg > overall_avg * 1.15:
                insights.append(
                    "⚠️ Your recent spending is higher than your average - consider reviewing expenses"
                )

        return insights

    def _get_spending_summary(self):
        """Get a quick spending summary for current month."""
        if FORCE_SQL_ALCHEMY:
            session = get_session()
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

        current_month = datetime.now().strftime("%Y-%m")

        # Total expenses this month
        if FORCE_SQL_ALCHEMY:
            total_expenses = (
                session.query(func.coalesce(func.sum(TransactionModel.amount), 0.0))
                .filter(
                    TransactionModel.type == "expense",
                    TransactionModel.date.like(f"{current_month}%"),
                )
                .scalar()
                or 0
            )
        else:
            cursor.execute(
                """
                SELECT SUM(amount) FROM transactions
                WHERE type = 'expense' AND strftime('%Y-%m', date) = ?
            """,
                (current_month,),
            )

            total_expenses = cursor.fetchone()[0] or 0

        # Total income this month
        if FORCE_SQL_ALCHEMY:
            total_income = (
                session.query(func.coalesce(func.sum(TransactionModel.amount), 0.0))
                .filter(
                    TransactionModel.type == "income",
                    TransactionModel.date.like(f"{current_month}%"),
                )
                .scalar()
                or 0
            )
        else:
            cursor.execute(
                """
                SELECT SUM(amount) FROM transactions
                WHERE type = 'income' AND strftime('%Y-%m', date) = ?
            """,
                (current_month,),
            )

            total_income = cursor.fetchone()[0] or 0

        # Top 5 expenses
        if FORCE_SQL_ALCHEMY:
            rows = (
                session.query(
                    TransactionModel.date,
                    TransactionModel.description,
                    TransactionModel.amount,
                    TransactionModel.category,
                )
                .filter(
                    TransactionModel.type == "expense",
                    TransactionModel.date.like(f"{current_month}%"),
                )
                .order_by(TransactionModel.amount.desc())
                .limit(5)
                .all()
            )
            top_expenses = [
                {"date": r[0], "description": r[1], "amount": r[2], "category": r[3]}
                for r in rows
            ]
        else:
            cursor.execute(
                """
                SELECT date, description, amount, category
                FROM transactions
                WHERE type = 'expense' AND strftime('%Y-%m', date) = ?
                ORDER BY amount DESC
                LIMIT 5
            """,
                (current_month,),
            )

            top_expenses = [
                {"date": date, "description": desc, "amount": amt, "category": cat}
                for date, desc, amt, cat in cursor.fetchall()
            ]

        if FORCE_SQL_ALCHEMY:
            session.close()
        else:
            conn.close()

        summary = {
            "type": "spending_summary",
            "tool": "finance_manager",
            "period": datetime.now().strftime("%B %Y"),
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net": round(total_income - total_expenses, 2),
            "top_expenses": top_expenses,
            "status": "surplus" if total_income > total_expenses else "deficit",
        }
        return {
            "type": "formatted_text",
            "tool": "finance_manager",
            "content": self.format_spending_summary(summary),
        }

    def _handle_add_goal(self, query: str) -> dict:
        """Handle financial goal creation."""
        return {
            "type": "interactive_form",
            "tool": "finance_manager",
            "form": {
                "title": "Create Financial Goal",
                "fields": [
                    {
                        "name": "name",
                        "type": "text",
                        "label": "Goal Name",
                        "required": True,
                    },
                    {
                        "name": "target_amount",
                        "type": "number",
                        "label": "Target Amount ($)",
                        "required": True,
                    },
                    {
                        "name": "deadline",
                        "type": "date",
                        "label": "Target Date",
                        "required": True,
                    },
                    {
                        "name": "priority",
                        "type": "select",
                        "label": "Priority",
                        "options": ["high", "medium", "low"],
                        "default": "medium",
                    },
                ],
            },
            "message": "Set up a new financial goal",
        }

    def add_goal(
        self, name: str, target_amount: float, deadline: str, priority: str = "medium"
    ) -> bool:
        """Add a new financial goal."""
        if FORCE_SQL_ALCHEMY:
            session = get_session()
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

        if FORCE_SQL_ALCHEMY:
            goal = FinancialGoalModel(
                name=name,
                target_amount=target_amount,
                deadline=deadline,
                priority=priority,
            )
            session.add(goal)
            session.commit()
            session.close()
        else:
            cursor.execute(
                """
                INSERT INTO financial_goals (name, target_amount, deadline, priority)
                VALUES (?, ?, ?, ?)
            """,
                (name, target_amount, deadline, priority),
            )
            conn.commit()
            conn.close()
        return True

    def _get_goals_status(self) -> dict:
        """Get status of all financial goals."""
        if FORCE_SQL_ALCHEMY:
            session = get_session()
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

        if FORCE_SQL_ALCHEMY:
            rows = (
                session.query(FinancialGoalModel)
                .order_by(
                    FinancialGoalModel.priority.desc(),
                    FinancialGoalModel.deadline.asc(),
                )
                .all()
            )
            goals = []
            for r in rows:
                goal_id, name, target, current, deadline, priority = (
                    r.id,
                    r.name,
                    r.target_amount,
                    r.current_amount,
                    r.deadline,
                    r.priority,
                )

                goal = FinancialGoal(
                    id=goal_id,
                    name=name,
                    target_amount=target,
                    current_amount=current,
                    deadline=deadline,
                    priority=priority,
                )

                goals.append(
                    {
                        "id": goal_id,
                        "name": name,
                        "target": target,
                        "current": current,
                        "remaining": goal.remaining_amount(),
                        "progress": round(goal.progress_percentage(), 1),
                        "deadline": deadline,
                        "days_remaining": goal.days_remaining(),
                        "priority": priority,
                        "status": (
                            "on_track" if goal.progress_percentage() > 50 else "behind"
                        ),
                    }
                )
        else:
            goals = []
            for goal_id, name, target, current, deadline, priority in cursor.fetchall():
                goal = FinancialGoal(
                    id=goal_id,
                    name=name,
                    target_amount=target,
                    current_amount=current,
                    deadline=deadline,
                    priority=priority,
                )

                goals.append(
                    {
                        "id": goal_id,
                        "name": name,
                        "target": target,
                        "current": current,
                        "remaining": goal.remaining_amount(),
                        "progress": round(goal.progress_percentage(), 1),
                        "deadline": deadline,
                        "days_remaining": goal.days_remaining(),
                        "priority": priority,
                        "status": (
                            "on_track" if goal.progress_percentage() > 50 else "behind"
                        ),
                    }
                )

        if FORCE_SQL_ALCHEMY:
            session.close()
        else:
            conn.close()

        return {
            "type": "goals_status",
            "tool": "finance_manager",
            "goals": goals,
            "total_goals": len(goals),
            "active_goals": len([g for g in goals if g["progress"] < 100]),
        }

    def _handle_grocery_list(self, query: str) -> dict:
        """Create or manage grocery list."""
        return {
            "type": "interactive_form",
            "tool": "finance_manager",
            "form": {
                "title": "Create Grocery List",
                "fields": [
                    {
                        "name": "name",
                        "type": "text",
                        "label": "List Name",
                        "default": f"Groceries {datetime.now().strftime('%m/%d')}",
                    },
                    {
                        "name": "items",
                        "type": "textarea",
                        "label": "Items (one per line)",
                        "placeholder": "Milk\nBread\nEggs\nChicken\nVegetables",
                    },
                ],
            },
            "message": "Create a new grocery list",
        }

    def create_grocery_list(self, name: str, items: List[str]) -> int:
        """Create a new grocery list with items."""
        if FORCE_SQL_ALCHEMY:
            session = get_session()
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

        # Create list
        if FORCE_SQL_ALCHEMY:
            gl = GroceryListModel(name=name)
            session.add(gl)
            session.commit()  # to populate id
            for item in items:
                gi = GroceryItemModel(list_id=gl.id, item_name=item.strip())
                session.add(gi)
            session.commit()
            list_id = gl.id
            session.close()
            return list_id
        else:
            cursor.execute(
                """
                INSERT INTO grocery_lists (name)
                VALUES (?)
            """,
                (name,),
            )

            list_id = cursor.lastrowid

            # Add items
            for item in items:
                cursor.execute(
                    """
                    INSERT INTO grocery_items (list_id, item_name)
                    VALUES (?, ?)
                """,
                    (list_id, item.strip()),
                )

            conn.commit()
            conn.close()
            return list_id

    def _show_grocery_lists(self) -> dict:
        """Show all grocery lists."""
        if FORCE_SQL_ALCHEMY:
            session = get_session()
        else:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

        if FORCE_SQL_ALCHEMY:
            lists = []
            rows = (
                session.query(GroceryListModel)
                .order_by(GroceryListModel.created_at.desc())
                .limit(10)
                .all()
            )
            for r in rows:
                total = len(r.items)
                checked = sum(1 for it in r.items if it.checked)
                lists.append(
                    {
                        "id": r.id,
                        "name": r.name,
                        "created": r.created_at,
                        "completed": bool(r.completed),
                        "total_items": total,
                        "checked_items": checked,
                    }
                )
        else:
            cursor.execute(
                """
                SELECT gl.id, gl.name, gl.created_at, gl.completed,
                       COUNT(gi.id) as total_items,
                       SUM(CASE WHEN gi.checked = 1 THEN 1 ELSE 0 END) as checked_items
                FROM grocery_lists gl
                LEFT JOIN grocery_items gi ON gl.id = gi.list_id
                GROUP BY gl.id
                ORDER BY gl.created_at DESC
                LIMIT 10
            """
            )

            lists = [
                {
                    "id": list_id,
                    "name": name,
                    "created": created,
                    "completed": bool(completed),
                    "total_items": total,
                    "checked_items": checked or 0,
                }
                for list_id, name, created, completed, total, checked in cursor.fetchall()
            ]

        if FORCE_SQL_ALCHEMY:
            session.close()
        else:
            conn.close()

        return {"type": "grocery_lists", "tool": "finance_manager", "lists": lists}

    def _provide_financial_advice(self) -> dict:
        """Provide personalized financial advice based on data."""
        # Get current financial state
        budget_status = self._get_budget_status()
        spending_analysis = self._analyze_spending_habits()
        goals_status = self._get_goals_status()

        advice = []

        # Budget advice
        if budget_status.get("summary", {}).get("categories_over_budget", 0) > 0:
            advice.append(
                {
                    "priority": "high",
                    "category": "Budget Management",
                    "suggestion": "You're over budget in some categories. Review and adjust your spending or increase budget limits.",
                    "action": "Check budget status for details",
                }
            )

        # Spending pattern advice
        patterns = spending_analysis.get("patterns", [])
        if any("increased" in p for p in patterns):
            advice.append(
                {
                    "priority": "medium",
                    "category": "Spending Trends",
                    "suggestion": "Your spending has increased recently. Consider tracking daily expenses more closely.",
                    "action": "Set up expense alerts",
                }
            )

        # Goal advice
        goals = goals_status.get("goals", [])
        behind_goals = [g for g in goals if g["status"] == "behind"]
        if behind_goals:
            advice.append(
                {
                    "priority": "medium",
                    "category": "Financial Goals",
                    "suggestion": f"You have {len(behind_goals)} goal(s) that need attention. Consider allocating more towards these goals.",
                    "action": "Review goal progress and adjust contributions",
                }
            )

        # General savings advice
        spending_summary = self._get_spending_summary()
        if spending_summary.get("status") == "surplus":
            surplus = spending_summary.get("net", 0)
            advice.append(
                {
                    "priority": "low",
                    "category": "Savings Opportunity",
                    "suggestion": f"You have a surplus of ${surplus:.2f} this month. Consider putting this towards your goals or emergency fund.",
                    "action": "Allocate surplus to savings or investments",
                }
            )

        return {
            "type": "financial_advice",
            "tool": "finance_manager",
            "advice": advice,
            "timestamp": datetime.now().isoformat(),
        }

    def _get_financial_overview(self) -> dict:
        """Get a complete financial overview."""
        return {
            "type": "financial_overview",
            "tool": "finance_manager",
            "sections": {
                "spending": self._get_spending_summary(),
                "budgets": self._get_budget_status(),
                "goals": self._get_goals_status(),
            },
            "message": "Here's your complete financial overview",
        }

    def execute(self, query: str):
        """Execute method for reasoning engine."""
        return self.run(query)
