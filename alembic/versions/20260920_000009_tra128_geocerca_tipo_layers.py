"""TRA-128: extend tipo_geocerca for secciones and district layers.

Revision ID: 20260920_000009
Revises: 20260920_000008
Create Date: 2026-09-20 00:00:09
"""

import sqlalchemy as sa

from alembic import op

revision = "20260920_000009"
down_revision = "20260920_000008"
branch_labels = None
depends_on = None

_NEW_TIPO_GEOCERCA_VALUES = (
    "SECCION",
    "DISTRITO_LOCAL",
    "DISTRITO_FEDERAL",
)


def upgrade() -> None:
    for value in _NEW_TIPO_GEOCERCA_VALUES:
        op.execute(
            sa.text(f"ALTER TYPE tipo_geocerca ADD VALUE IF NOT EXISTS '{value}'")
        )


def downgrade() -> None:
    # PostgreSQL cannot remove enum values safely; DISTRITO and prior values remain.
    pass
