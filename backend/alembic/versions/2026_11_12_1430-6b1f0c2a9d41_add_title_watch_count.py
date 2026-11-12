"""add titles.watch_count

Revision ID: 6b1f0c2a9d41
Revises: 2ccc037359b2
Create Date: 2026-11-12 14:30:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6b1f0c2a9d41'
down_revision: Union[str, Sequence[str], None] = '2ccc037359b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('titles', sa.Column('watch_count', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('titles', 'watch_count')
