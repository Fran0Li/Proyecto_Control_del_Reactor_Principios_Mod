"""version de sesion

Revision ID: 36e6f2691c31
Revises: 24a1ea29db65
Create Date: 2026-10-19 19:02:33.918204

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '36e6f2691c31'
down_revision: Union[str, Sequence[str], None] = '24a1ea29db65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('usuarios', sa.Column('version_sesion', sa.Integer(), server_default='0', nullable=False))


def downgrade() -> None:
    op.drop_column('usuarios', 'version_sesion')
