"""add category column to receiptitem

Revision ID: 0001_add_category
Revises: 
Create Date: 2025-12-18 00:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_add_category'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add category column if it does not exist (safe for SQLite using ALTER TABLE)
    op.add_column('receiptitem', sa.Column('category', sa.String(), nullable=True))


def downgrade():
    op.drop_column('receiptitem', 'category')
