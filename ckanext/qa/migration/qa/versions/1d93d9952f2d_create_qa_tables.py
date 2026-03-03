"""Create QA tables

Revision ID: 1d93d9952f2d
Revises:
Create Date: 2025-12-18 11:44:40.242757

"""

from alembic import op
from uuid import uuid4
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1d93d9952f2d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    engine = op.get_bind()
    inspector = sa.inspect(engine)
    tables = inspector.get_table_names()
    if "qa" not in tables:
        op.create_table(
            "qa",
            sa.Column("id", sa.UnicodeText, primary_key=True, default=uuid4),
            sa.Column("package_id", sa.UnicodeText, nullable=False, index=True),
            sa.Column("resource_id", sa.UnicodeText, nullable=False, index=True),
            sa.Column("resource_timestamp", sa.DateTime),  # key to resource_revision
            sa.Column("archival_timestamp", sa.DateTime),
            sa.Column("openness_score", sa.Integer),
            sa.Column("openness_score_reason", sa.UnicodeText),
            sa.Column("format", sa.UnicodeText),
            sa.Column("created", sa.DateTime, default=sa.func.current_timestamp()),
            sa.Column("updated", sa.DateTime, default=sa.func.current_timestamp()),
        )


def downgrade():
    op.drop_table("qa")
