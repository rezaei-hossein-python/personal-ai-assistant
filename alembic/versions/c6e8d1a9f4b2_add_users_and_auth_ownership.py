"""Add users and auth ownership

Revision ID: c6e8d1a9f4b2
Revises: a833cda87b74
Create Date: 2026-07-18 22:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c6e8d1a9f4b2'
down_revision: Union[str, Sequence[str], None] = 'a833cda87b74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    conversation_columns = {
        column["name"]
        for column in inspector.get_columns("conversations")
    }
    if "user_id" not in conversation_columns:
        op.add_column(
            "conversations",
            sa.Column("user_id", sa.Integer(), nullable=True),
        )
        op.create_index(
            op.f("ix_conversations_user_id"),
            "conversations",
            ["user_id"],
            unique=False,
        )

    if "title" not in conversation_columns:
        op.add_column(
            "conversations",
            sa.Column(
                "title",
                sa.String(),
                nullable=False,
                server_default="New Conversation",
            ),
        )
        op.alter_column("conversations", "title", server_default=None)

    message_columns = {
        column["name"]
        for column in inspector.get_columns("messages")
    }
    if "user_id" not in message_columns:
        op.add_column(
            "messages",
            sa.Column("user_id", sa.Integer(), nullable=True),
        )
        op.create_index(
            op.f("ix_messages_user_id"),
            "messages",
            ["user_id"],
            unique=False,
        )

    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TABLE conversations "
            "DROP CONSTRAINT IF EXISTS conversations_conversation_id_key"
        )
        op.execute("DROP INDEX IF EXISTS ix_conversations_conversation_id")
        op.create_index(
            op.f('ix_conversations_conversation_id'),
            'conversations',
            ['conversation_id'],
            unique=False
        )
    else:
        op.drop_index(
            op.f('ix_conversations_conversation_id'),
            table_name='conversations'
        )
        op.create_index(
            op.f('ix_conversations_conversation_id'),
            'conversations',
            ['conversation_id'],
            unique=False
        )

    op.create_index(
        'ix_conversations_user_conversation_id',
        'conversations',
        ['user_id', 'conversation_id'],
        unique=True
    )

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index(
        'ix_conversations_user_conversation_id',
        table_name='conversations'
    )
    op.drop_index(op.f('ix_conversations_conversation_id'), table_name='conversations')
    op.create_index(
        op.f('ix_conversations_conversation_id'),
        'conversations',
        ['conversation_id'],
        unique=True
    )
