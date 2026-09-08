"""initial_schema

Revision ID: ad6586e1e046
Revises: 
Create Date: 2026-07-30 14:50:26.908691

NOTE: This migration was regenerated to fix an inverted upgrade/downgrade bug.
      The original auto-generated file had upgrade() dropping tables and
      downgrade() creating them — exactly backwards.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'ad6586e1e046'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the full WalletAI schema from scratch."""

    # ── Enum types ────────────────────────────────────────────────────────────
    # Create enums explicitly so we control the values (including TRANSFER and SUCCESS)
    accounttype = postgresql.ENUM('CASH', 'CARD', 'BANK', name='accounttype', create_type=False)
    accounttype.create(op.get_bind(), checkfirst=True)

    insight_type_enum = postgresql.ENUM(
        'WARNING', 'TIP', 'INFO', 'SUCCESS',
        name='insight_type_enum', create_type=False
    )
    insight_type_enum.create(op.get_bind(), checkfirst=True)

    transaction_type_enum = postgresql.ENUM(
        'EXPENSE', 'INCOME', 'TRANSFER',
        name='transaction_type_enum', create_type=False
    )
    transaction_type_enum.create(op.get_bind(), checkfirst=True)

    # ── users ─────────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id',              postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email',           sa.String(320), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name',       sa.String(200), nullable=True),
        sa.Column('is_active',       sa.Boolean(),   nullable=False, server_default='true'),
        sa.Column('created_at',      sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ── categories (self-referential) ─────────────────────────────────────────
    op.create_table(
        'categories',
        sa.Column('id',        postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name',      sa.String(200), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('icon',      sa.String(20),  nullable=True),
        sa.Column('color',     sa.String(9),   nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['categories.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_categories_name',      'categories', ['name'],      unique=False)
    op.create_index('ix_categories_parent_id', 'categories', ['parent_id'], unique=False)

    # ── accounts ──────────────────────────────────────────────────────────────
    op.create_table(
        'accounts',
        sa.Column('id',       postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id',  postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name',     sa.String(200), nullable=False),
        sa.Column('type',     sa.Enum('CASH', 'CARD', 'BANK', name='accounttype'), nullable=False),
        sa.Column('balance',  sa.Numeric(15, 2), nullable=False, server_default='0.00'),
        sa.Column('currency', sa.String(3),  nullable=False, server_default='INR'),
        sa.Column('color',    sa.String(9),  nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_accounts_user_id', 'accounts', ['user_id'], unique=False)

    # ── transactions ──────────────────────────────────────────────────────────
    op.create_table(
        'transactions',
        sa.Column('id',          postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id',     postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('account_id',  postgresql.UUID(as_uuid=True), nullable=True),   # SET NULL on account delete
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('amount',      sa.Numeric(12, 2), nullable=False),
        sa.Column('type',        sa.Enum('EXPENSE', 'INCOME', 'TRANSFER',
                                         name='transaction_type_enum'), nullable=False),
        sa.Column('note',        sa.Text(),   nullable=True),
        sa.Column('tags',        postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('date',        sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.Column('created_at',  sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'],     ['users.id'],      ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['account_id'],  ['accounts.id'],   ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_transactions_user_id',  'transactions', ['user_id'], unique=False)
    op.create_index('ix_transactions_date',     'transactions', ['date'],    unique=False)

    # ── ai_insights ───────────────────────────────────────────────────────────
    op.create_table(
        'ai_insights',
        sa.Column('id',           postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id',      postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('insight_text', sa.Text(),    nullable=False),
        sa.Column('insight_type', sa.Enum('WARNING', 'TIP', 'INFO', 'SUCCESS',
                                          name='insight_type_enum'), nullable=False),
        sa.Column('is_dismissed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at',   sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_ai_insights_user_id',    'ai_insights', ['user_id'],    unique=False)
    op.create_index('ix_ai_insights_created_at', 'ai_insights', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop the full WalletAI schema."""

    # Drop tables in reverse dependency order
    op.drop_index('ix_ai_insights_created_at', table_name='ai_insights')
    op.drop_index('ix_ai_insights_user_id',    table_name='ai_insights')
    op.drop_table('ai_insights')

    op.drop_index('ix_transactions_date',    table_name='transactions')
    op.drop_index('ix_transactions_user_id', table_name='transactions')
    op.drop_table('transactions')

    op.drop_index('ix_accounts_user_id', table_name='accounts')
    op.drop_table('accounts')

    op.drop_index('ix_categories_parent_id', table_name='categories')
    op.drop_index('ix_categories_name',      table_name='categories')
    op.drop_table('categories')

    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')

    # Drop enum types last (after all tables that reference them are gone)
    op.execute('DROP TYPE IF EXISTS transaction_type_enum')
    op.execute('DROP TYPE IF EXISTS insight_type_enum')
    op.execute('DROP TYPE IF EXISTS accounttype')
