"""detalle de los eventos (US-17)

Revision ID: e989458952f6
Revises: 5a7c2e9d41b3
Create Date: 2026-11-19 00:41:12.508113

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e989458952f6'
down_revision: Union[str, Sequence[str], None] = '5a7c2e9d41b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('eventos', sa.Column('jugador_id', sa.Integer(), nullable=True))
    op.add_column('eventos', sa.Column('datos', sa.JSON(), nullable=True))
    op.create_foreign_key('eventos_jugador_id_fkey', 'eventos', 'usuarios', ['jugador_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('eventos_jugador_id_fkey', 'eventos', type_='foreignkey')
    op.drop_column('eventos', 'datos')
    op.drop_column('eventos', 'jugador_id')
