"""intentos fallidos de login

Revision ID: b43a10b4ebc1
Revises: db7e5454f22c
Create Date: 2026-10-19 17:40:12.481920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b43a10b4ebc1'
down_revision: Union[str, Sequence[str], None] = 'db7e5454f22c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('intentos_fallidos', sa.Integer(), server_default='0', nullable=False))
    op.add_column('usuarios', sa.Column('bloqueado_hasta', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('usuarios', 'bloqueado_hasta')
    op.drop_column('usuarios', 'intentos_fallidos')
