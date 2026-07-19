"""Add pgvector embeddings

Revision ID: e7b9c1d2a3f4
Revises: d4f9a2b7c8e1
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7b9c1d2a3f4'
down_revision: Union[str, Sequence[str], None] = 'd4f9a2b7c8e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIMENSION = 1536


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute(
            f"ALTER TABLE document_chunks "
            f"ADD COLUMN embedding vector({EMBEDDING_DIMENSION})"
        )
        op.execute(
            "CREATE INDEX ix_document_chunks_embedding_cosine "
            "ON document_chunks "
            "USING ivfflat (embedding vector_cosine_ops) "
            "WITH (lists = 100)"
        )
    else:
        op.add_column(
            "document_chunks",
            sa.Column("embedding", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding_cosine")
        op.execute("ALTER TABLE document_chunks DROP COLUMN embedding")
    else:
        op.drop_column("document_chunks", "embedding")
