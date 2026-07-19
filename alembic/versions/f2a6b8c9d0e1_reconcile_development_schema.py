"""Reconcile development schema

Revision ID: f2a6b8c9d0e1
Revises: e7b9c1d2a3f4
Create Date: 2026-07-19 00:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f2a6b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e7b9c1d2a3f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    memory_columns = {
        column["name"]
        for column in inspector.get_columns("memories")
    }
    memory_indexes = {
        index["name"]
        for index in inspector.get_indexes("memories")
    }
    if "updated_at" not in memory_columns:
        op.add_column(
            "memories",
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("CURRENT_TIMESTAMP"),
                nullable=True,
            ),
        )
    if "ix_memories_category" not in memory_indexes:
        op.create_index(
            op.f("ix_memories_category"),
            "memories",
            ["category"],
            unique=False,
        )
    if "ix_memories_key" not in memory_indexes:
        op.create_index(
            op.f("ix_memories_key"),
            "memories",
            ["key"],
            unique=False,
        )
    if "ix_memories_user_id" not in memory_indexes:
        op.create_index(
            op.f("ix_memories_user_id"),
            "memories",
            ["user_id"],
            unique=False,
        )

    if bind.dialect.name == "postgresql":
        op.execute(
            "UPDATE conversations "
            "SET title = 'New Conversation' "
            "WHERE title IS NULL"
        )
        op.alter_column(
            "conversations",
            "conversation_id",
            existing_type=sa.String(),
            nullable=False,
        )
        op.alter_column(
            "conversations",
            "title",
            existing_type=sa.String(),
            nullable=False,
        )

        op.execute(
            "UPDATE messages "
            "SET conversation_id = 'recovered-conversation' "
            "WHERE conversation_id IS NULL"
        )
        op.execute(
            "INSERT INTO conversations (conversation_id, title) "
            "SELECT DISTINCT messages.conversation_id, 'Recovered Conversation' "
            "FROM messages "
            "LEFT JOIN conversations "
            "ON conversations.conversation_id = messages.conversation_id "
            "WHERE messages.conversation_id IS NOT NULL "
            "AND conversations.id IS NULL"
        )
        op.execute(
            "UPDATE messages SET role = 'unknown' WHERE role IS NULL"
        )
        op.execute(
            "UPDATE messages SET content = '' WHERE content IS NULL"
        )
        op.alter_column(
            "messages",
            "conversation_id",
            existing_type=sa.String(),
            nullable=False,
        )
        op.alter_column(
            "messages",
            "role",
            existing_type=sa.String(),
            nullable=False,
        )
        op.alter_column(
            "messages",
            "content",
            existing_type=sa.Text(),
            nullable=False,
        )

        op.execute(
            "ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key"
        )


def downgrade() -> None:
    """Downgrade schema."""
    pass
