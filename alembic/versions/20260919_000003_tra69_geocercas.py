"""TRA-69: geocercas geoespaciales versionadas

Revision ID: 20260919_000003
Revises: 20260915_000002
Create Date: 2026-09-19 00:00:03
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

revision = "20260919_000003"
down_revision = "20260915_000002"
branch_labels = None
depends_on = None

tipo_geocerca = sa.Enum("ESTADO", "MUNICIPIO", "DISTRITO", name="tipo_geocerca")


def upgrade() -> None:
    tipo_geocerca.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "geocercas",
        sa.Column("id", sa.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "tipo",
            sa.Enum("ESTADO", "MUNICIPIO", "DISTRITO", name="tipo_geocerca"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=True),
        sa.Column("codigo_padre", sa.String(50), nullable=True),
        sa.Column(
            "geometria",
            Geometry("GEOMETRY", srid=4326),
            nullable=False,
        ),
        sa.Column("fuente", sa.String(255), nullable=False),
        sa.Column("hash_geometria", sa.String(64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("vigente", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "importado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("importado_por", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_geocercas"),
        sa.UniqueConstraint("hash_geometria", "tipo", name="uq_geocerca_hash_tipo"),
    )

    op.create_index("ix_geocercas_tipo", "geocercas", ["tipo"])
    op.create_index("ix_geocercas_codigo", "geocercas", ["codigo"])
    op.create_index("ix_geocercas_codigo_padre", "geocercas", ["codigo_padre"])
    op.create_index("ix_geocercas_vigente", "geocercas", ["vigente"])
    op.create_index(
        "ix_geocercas_geometria",
        "geocercas",
        ["geometria"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("ix_geocercas_geometria", table_name="geocercas")
    op.drop_index("ix_geocercas_vigente", table_name="geocercas")
    op.drop_index("ix_geocercas_codigo_padre", table_name="geocercas")
    op.drop_index("ix_geocercas_codigo", table_name="geocercas")
    op.drop_index("ix_geocercas_tipo", table_name="geocercas")
    op.drop_table("geocercas")

    bind = op.get_bind()
    tipo_geocerca.drop(bind, checkfirst=True)
