"""Add ownership and composite conversation/message relationships.

Revision ID: 8f1a2b3c4d5e
Revises: f2a6b8c9d0e1
Create Date: 2026-07-19 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "8f1a2b3c4d5e"
down_revision: Union[str, Sequence[str], None] = "f2a6b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONVERSATION_USER_FK = "fk_conversations_user"
MESSAGE_USER_FK = "fk_messages_user"
MESSAGE_CONVERSATION_FK = "fk_messages_conversation_owner"
CONVERSATION_UNIQUE = "uq_conversations_user_conversation"
CONVERSATION_USER_CONVERSATION_INDEX = "ix_conversations_user_conversation_id"


def _scalar(sql: str):
    return op.get_bind().execute(sa.text(sql)).scalar()


def _validate_existing_data() -> None:
    invalid_conversation_users = _scalar(
        """
        SELECT COUNT(*)
        FROM conversations AS c
        LEFT JOIN users AS u ON u.id = c.user_id
        WHERE c.user_id IS NOT NULL
          AND u.id IS NULL
        """
    )
    invalid_message_users = _scalar(
        """
        SELECT COUNT(*)
        FROM messages AS m
        LEFT JOIN users AS u ON u.id = m.user_id
        WHERE m.user_id IS NOT NULL
          AND u.id IS NULL
        """
    )
    duplicate_owned_conversations = _scalar(
        """
        SELECT COUNT(*)
        FROM (
            SELECT user_id, conversation_id
            FROM conversations
            WHERE user_id IS NOT NULL
            GROUP BY user_id, conversation_id
            HAVING COUNT(*) > 1
        ) AS duplicates
        """
    )

    errors = []
    if invalid_conversation_users:
        errors.append(
            f"{invalid_conversation_users} conversations.user_id values "
            "do not reference users.id"
        )
    if invalid_message_users:
        errors.append(
            f"{invalid_message_users} messages.user_id values do not "
            "reference users.id"
        )
    if duplicate_owned_conversations:
        errors.append(
            f"{duplicate_owned_conversations} duplicate non-null "
            "(user_id, conversation_id) conversation keys exist"
        )

    if errors:
        raise RuntimeError(
            "Cannot add conversation/message foreign keys until existing "
            "data is repaired: " + "; ".join(errors)
        )


def _recover_missing_owned_conversations() -> None:
    op.execute(
        """
        INSERT INTO conversations (conversation_id, user_id, title, created_at)
        SELECT DISTINCT
               m.conversation_id,
               m.user_id,
               'Recovered Conversation',
               CURRENT_TIMESTAMP
        FROM messages AS m
        LEFT JOIN conversations AS c
          ON c.user_id = m.user_id
         AND c.conversation_id = m.conversation_id
        WHERE m.user_id IS NOT NULL
          AND c.id IS NULL
        """
    )


def _constraint_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    names = {
        constraint["name"]
        for constraint in inspector.get_foreign_keys(table_name)
        if constraint.get("name")
    }
    names.update(
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    )
    return names


def _index_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {
        index["name"]
        for index in inspector.get_indexes(table_name)
        if index.get("name")
    }


def upgrade() -> None:
    """Upgrade schema with explicit ownership and conversation/message FKs."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if not {"users", "conversations", "messages"}.issubset(existing_tables):
        return

    _validate_existing_data()
    _recover_missing_owned_conversations()

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("conversations", recreate="always") as batch_op:
            batch_op.create_unique_constraint(
                CONVERSATION_UNIQUE,
                ["user_id", "conversation_id"],
            )
            batch_op.create_foreign_key(
                CONVERSATION_USER_FK,
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )

        with op.batch_alter_table("messages", recreate="always") as batch_op:
            batch_op.create_foreign_key(
                MESSAGE_USER_FK,
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.create_foreign_key(
                MESSAGE_CONVERSATION_FK,
                "conversations",
                ["user_id", "conversation_id"],
                ["user_id", "conversation_id"],
                ondelete="CASCADE",
            )
        return

    conversation_constraints = _constraint_names("conversations")
    message_constraints = _constraint_names("messages")
    conversation_indexes = _index_names("conversations")

    if CONVERSATION_UNIQUE not in conversation_constraints:
        op.create_unique_constraint(
            CONVERSATION_UNIQUE,
            "conversations",
            ["user_id", "conversation_id"],
        )

    if CONVERSATION_USER_FK not in conversation_constraints:
        op.create_foreign_key(
            CONVERSATION_USER_FK,
            "conversations",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    if CONVERSATION_USER_CONVERSATION_INDEX not in conversation_indexes:
        op.create_index(
            CONVERSATION_USER_CONVERSATION_INDEX,
            "conversations",
            ["user_id", "conversation_id"],
            unique=True,
        )

    if MESSAGE_USER_FK not in message_constraints:
        op.create_foreign_key(
            MESSAGE_USER_FK,
            "messages",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

    if MESSAGE_CONVERSATION_FK not in message_constraints:
        op.create_foreign_key(
            MESSAGE_CONVERSATION_FK,
            "messages",
            "conversations",
            ["user_id", "conversation_id"],
            ["user_id", "conversation_id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    """Downgrade schema to the previous relationship constraints."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if not {"conversations", "messages"}.issubset(existing_tables):
        return

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("messages", recreate="always") as batch_op:
            batch_op.drop_constraint(MESSAGE_CONVERSATION_FK, type_="foreignkey")
            batch_op.drop_constraint(MESSAGE_USER_FK, type_="foreignkey")

        with op.batch_alter_table("conversations", recreate="always") as batch_op:
            batch_op.drop_constraint(CONVERSATION_USER_FK, type_="foreignkey")
            batch_op.drop_constraint(CONVERSATION_UNIQUE, type_="unique")
        return

    message_constraints = _constraint_names("messages")
    conversation_constraints = _constraint_names("conversations")

    if MESSAGE_CONVERSATION_FK in message_constraints:
        op.drop_constraint(MESSAGE_CONVERSATION_FK, "messages", type_="foreignkey")
    if MESSAGE_USER_FK in message_constraints:
        op.drop_constraint(MESSAGE_USER_FK, "messages", type_="foreignkey")
    if CONVERSATION_USER_FK in conversation_constraints:
        op.drop_constraint(CONVERSATION_USER_FK, "conversations", type_="foreignkey")
    if CONVERSATION_UNIQUE in conversation_constraints:
        op.drop_constraint(CONVERSATION_UNIQUE, "conversations", type_="unique")
