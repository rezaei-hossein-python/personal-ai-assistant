"""Add documents and chunks

Revision ID: d4f9a2b7c8e1
Revises: c6e8d1a9f4b2
Create Date: 2026-07-18 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4f9a2b7c8e1'
down_revision: Union[str, Sequence[str], None] = 'c6e8d1a9f4b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('content_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('processing_status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.String(length=500), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column(
            'uploaded_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=True
        ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)
    op.create_index(
        op.f('ix_documents_processing_status'),
        'documents',
        ['processing_status'],
        unique=False
    )
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)

    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ['document_id'],
            ['documents.id'],
            ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_document_chunks_document_id'),
        'document_chunks',
        ['document_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_document_chunks_id'),
        'document_chunks',
        ['id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_document_chunks_id'), table_name='document_chunks')
    op.drop_index(
        op.f('ix_document_chunks_document_id'),
        table_name='document_chunks'
    )
    op.drop_table('document_chunks')
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
    op.drop_index(
        op.f('ix_documents_processing_status'),
        table_name='documents'
    )
    op.drop_index(op.f('ix_documents_id'), table_name='documents')
    op.drop_table('documents')
