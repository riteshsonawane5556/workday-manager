"""split session_history into session and session_message

Revision ID: a1b2c3d4e5f6
Revises: 7983b7d50d48
Create Date: 2026-06-09 00:00:00.000000

"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7983b7d50d48'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'session',
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('session_name', sa.String(), nullable=True),
        sa.Column('calendar_action_open', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('session_id'),
    )
    op.create_table(
        'session_message',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('agent_type', sa.String(32), nullable=False),
        sa.Column('role', sa.String(16), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('message_json', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['session.session_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_session_message_lookup', 'session_message', ['session_id', 'agent_type', 'sequence'])

    conn = op.get_bind()
    rows = conn.execute(
        sa.text('SELECT session_id, planner, calendar_action, synthesize, calendar_action_open, updated_at FROM session_history')
    ).fetchall()

    for row in rows:
        conn.execute(
            sa.text(
                'INSERT INTO session (session_id, calendar_action_open, updated_at) '
                'VALUES (:sid, :open, :upd)'
            ),
            {'sid': row.session_id, 'open': row.calendar_action_open, 'upd': row.updated_at},
        )
        for agent_type, blob in (
            ('planner', row.planner),
            ('calendar_action', row.calendar_action),
            ('synthesize', row.synthesize),
        ):
            try:
                messages = json.loads(blob or '[]')
            except Exception:
                messages = []
            for seq, msg_dict in enumerate(messages):
                role = msg_dict.get('kind', 'request')
                conn.execute(
                    sa.text(
                        'INSERT INTO session_message (session_id, agent_type, role, sequence, message_json) '
                        'VALUES (:sid, :at, :role, :seq, :json)'
                    ),
                    {
                        'sid': row.session_id,
                        'at': agent_type,
                        'role': role,
                        'seq': seq,
                        'json': json.dumps(msg_dict),
                    },
                )

    op.drop_table('session_history')


def downgrade() -> None:
    op.create_table(
        'session_history',
        sa.Column('session_id', sa.String(), nullable=False),
        sa.Column('planner', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('calendar_action', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('synthesize', sa.Text(), nullable=False, server_default='[]'),
        sa.Column('calendar_action_open', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('session_id'),
    )
    op.drop_index('ix_session_message_lookup', table_name='session_message')
    op.drop_table('session_message')
    op.drop_table('session')
