<%!
from alembic import op
import sqlalchemy as sa
%>
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | none}
Create Date: ${create_date}
"""

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade():
    pass


def downgrade():
    pass
