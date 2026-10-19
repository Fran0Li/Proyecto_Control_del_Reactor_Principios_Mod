"""perfil del jugador

Revision ID: b124d9b1c989
Revises: 636a9f8ea937
Create Date: 2026-10-19 20:31:16.640275

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b124d9b1c989'
down_revision: Union[str, Sequence[str], None] = '636a9f8ea937'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('descripcion', sa.String(length=200), server_default='', nullable=False))
    op.add_column('usuarios', sa.Column('avatar', sa.String(length=20), server_default='azul', nullable=False))


def downgrade() -> None:
    op.drop_column('usuarios', 'avatar')
    op.drop_column('usuarios', 'descripcion')
