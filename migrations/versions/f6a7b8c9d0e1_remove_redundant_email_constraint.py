"""remove redundant email constraint

Revision ID: f6a7b8c9d0e1
Revises: e4f1a2b3c4d5
"""

from collections.abc import Sequence

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e4f1a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keep the model's unique email index without a duplicate constraint index."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("uq_users_email", type_="unique")


def downgrade() -> None:
    """Restore the explicit unique constraint when reverting this revision."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.create_unique_constraint(op.f("uq_users_email"), ["email"])
