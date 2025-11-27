"""add ai tables

Revision ID: add_ai_tables
Revises: 
Create Date: 2025-11-25

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_ai_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # AI Conversations
    op.create_table(
        'ai_conversations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('user_message', sa.Text(), nullable=False),
        sa.Column('ai_response', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_conversations_id'), 'ai_conversations', ['id'], unique=False)
    
    # AI Proactive Messages
    op.create_table(
        'ai_proactive_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('ai_analysis', sa.Text(), nullable=True),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('was_read', sa.Boolean(), nullable=True),
        sa.Column('client_responded', sa.Boolean(), nullable=True),
        sa.Column('resulted_in_order', sa.Boolean(), nullable=True),
        sa.Column('order_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_proactive_messages_id'), 'ai_proactive_messages', ['id'], unique=False)
    
    # AI Settings
    op.create_table(
        'ai_agent_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True),
        sa.Column('send_time', sa.Time(), nullable=True),
        sa.Column('send_days', sa.String(length=50), nullable=True),
        sa.Column('exclude_holidays', sa.Boolean(), nullable=True),
        sa.Column('trigger_days_no_order', sa.Integer(), nullable=True),
        sa.Column('trigger_bonus_amount', sa.Integer(), nullable=True),
        sa.Column('trigger_bonus_expiry_days', sa.Integer(), nullable=True),
        sa.Column('max_messages_per_day', sa.Integer(), nullable=True),
        sa.Column('min_days_between_messages', sa.Integer(), nullable=True),
        sa.Column('sales_aggressiveness', sa.Integer(), nullable=True),
        sa.Column('excluded_dates', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_agent_settings_id'), 'ai_agent_settings', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_ai_agent_settings_id'), table_name='ai_agent_settings')
    op.drop_table('ai_agent_settings')
    op.drop_index(op.f('ix_ai_proactive_messages_id'), table_name='ai_proactive_messages')
    op.drop_table('ai_proactive_messages')
    op.drop_index(op.f('ix_ai_conversations_id'), table_name='ai_conversations')
    op.drop_table('ai_conversations')