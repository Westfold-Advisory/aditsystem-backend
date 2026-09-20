"""TRA-128: remove legacy generic DISTRITO geocerca rows.

Revision ID: 20260920_000010
Revises: 20260920_000009
Create Date: 2026-09-20 00:00:10

The enum value ``DISTRITO`` remains in ``tipo_geocerca`` for compatibility;
only obsolete rows are deleted after INE DISTRITO_LOCAL/DISTRITO_FEDERAL import.
"""

import sqlalchemy as sa

from alembic import op

revision = "20260920_000010"
down_revision = "20260920_000009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM persona_geocercas pg
            USING geocercas g
            WHERE pg.geocerca_id = g.id
              AND g.tipo = 'DISTRITO'
            """
        )
    )
    op.execute(sa.text("DELETE FROM geocercas WHERE tipo = 'DISTRITO'"))


def downgrade() -> None:
    # Data removal is intentional; enum value DISTRITO is not restored.
    pass
