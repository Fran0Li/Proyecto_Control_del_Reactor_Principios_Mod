"""logros de los jugadores (US-27)

Revision ID: 5a7c2e9d41b3
Revises: b124d9b1c989
Create Date: 2026-11-16 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5a7c2e9d41b3'
down_revision: Union[str, Sequence[str], None] = 'b124d9b1c989'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'logros_jugador',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('jugador_id', sa.Integer(), nullable=False),
        sa.Column('logro', sa.String(length=50), nullable=False),
        sa.Column('partida_id', sa.Integer(), nullable=True),
        sa.Column('obtenido_en', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['jugador_id'], ['usuarios.id']),
        sa.ForeignKeyConstraint(['partida_id'], ['partidas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jugador_id', 'logro', name='uq_logro_por_jugador'),
    )
    op.create_index(op.f('ix_logros_jugador_jugador_id'), 'logros_jugador', ['jugador_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_logros_jugador_jugador_id'), table_name='logros_jugador')
    op.drop_table('logros_jugador')
