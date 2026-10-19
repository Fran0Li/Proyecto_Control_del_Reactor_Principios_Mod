"""cuentas de google

Revision ID: 636a9f8ea937
Revises: 36e6f2691c31
Create Date: 2026-10-19 19:48:05.117392

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '636a9f8ea937'
down_revision: Union[str, Sequence[str], None] = '36e6f2691c31'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('google_id', sa.String(length=64), nullable=True))
    op.create_unique_constraint('usuarios_google_id_key', 'usuarios', ['google_id'])
    op.alter_column('usuarios', 'contrasena_hash', existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column('usuarios', 'contrasena_hash', existing_type=sa.String(length=255), nullable=False)
    op.drop_constraint('usuarios_google_id_key', 'usuarios', type_='unique')
    op.drop_column('usuarios', 'google_id')
