"""rol de administrador (US-28)

Revision ID: 14c073bee5eb
Revises: e989458952f6
Create Date: 2026-11-19 00:22:39.805504

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '14c073bee5eb'
down_revision: Union[str, Sequence[str], None] = 'e989458952f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # las cuentas que ya existen quedan como jugadores sin bloquear
    op.add_column(
        'usuarios', sa.Column('rol', sa.String(length=20), server_default='jugador', nullable=False)
    )
    op.add_column(
        'usuarios',
        sa.Column('bloqueado', sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column('usuarios', 'bloqueado')
    op.drop_column('usuarios', 'rol')
