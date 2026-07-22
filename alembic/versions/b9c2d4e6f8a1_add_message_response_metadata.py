"""Add assistant response metadata to messages.

Revision ID: b9c2d4e6f8a1
Revises: 8f1a2b3c4d5e
Create Date: 2026-07-21 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9c2d4e6f8a1"
down_revision: Union[str, Sequence[str], None] = "8f1a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    """Upgrade schema."""
    if "response_metadata" in _column_names("messages"):
        return

    op.add_column(
        "messages",
        sa.Column("response_metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    if "response_metadata" not in _column_names("messages"):
        return

    op.drop_column("messages", "response_metadata")
