"""TRA-127: persona address, coordinates, and community needs.

Revision ID: 20260920_000011
Revises: 20260920_000010
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260920_000011"
down_revision = "20260920_000010"
branch_labels = None
depends_on = None

necesidad_comunidad = postgresql.ENUM(
    "INSEGURIDAD",
    "FALTA_ALUMBRADO_PUBLICO",
    "CALLES_MAL_ESTADO",
    "FALTA_AGUA_POTABLE",
    "PROBLEMAS_DRENAJE",
    "RECOLECCION_BASURA_DEFICIENTE",
    "FALTA_LIMPIEZA",
    "FALTA_TRANSPORTE_PUBLICO",
    "FALTA_PARQUES_ESPACIOS_RECREATIVOS",
    "VENTA_CONSUMO_DROGAS",
    "FALTA_ATENCION_MEDICA_CERCANA",
    "FALTA_APOYOS_SOCIALES",
    "FALTA_EMPLEO",
    "FALTA_ATENCION_ADULTOS_MAYORES",
    "FALTA_ATENCION_JOVENES",
    name="necesidad_comunidad",
    create_type=False,
)


def upgrade() -> None:
    necesidad_comunidad.create(op.get_bind(), checkfirst=True)

    for name, col_type in (
        ("calle", "VARCHAR(200)"),
        ("numero_exterior", "VARCHAR(30)"),
        ("numero_interior", "VARCHAR(30)"),
        ("colonia", "VARCHAR(120)"),
        ("codigo_postal", "VARCHAR(10)"),
        ("entre_calles", "VARCHAR(255)"),
        ("latitud", "NUMERIC(9, 6)"),
        ("longitud", "NUMERIC(10, 6)"),
    ):
        op.execute(
            sa.text(f"ALTER TABLE personas ADD COLUMN IF NOT EXISTS {name} {col_type}")
        )

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'persona_coords_pair'
              ) THEN
                ALTER TABLE personas ADD CONSTRAINT persona_coords_pair
                  CHECK (
                    (latitud IS NULL AND longitud IS NULL)
                    OR (latitud IS NOT NULL AND longitud IS NOT NULL)
                  );
              END IF;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'persona_latitud_range'
              ) THEN
                ALTER TABLE personas ADD CONSTRAINT persona_latitud_range
                  CHECK (latitud IS NULL OR (latitud >= -90 AND latitud <= 90));
              END IF;
            END $$;
            """
        )
    )
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'persona_longitud_range'
              ) THEN
                ALTER TABLE personas ADD CONSTRAINT persona_longitud_range
                  CHECK (longitud IS NULL OR (longitud >= -180 AND longitud <= 180));
              END IF;
            END $$;
            """
        )
    )

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "persona_necesidades_comunidad" not in inspector.get_table_names():
        op.create_table(
            "persona_necesidades_comunidad",
            sa.Column("persona_id", postgresql.UUID(as_uuid=False), nullable=False),
            sa.Column("necesidad", necesidad_comunidad, nullable=False),
            sa.ForeignKeyConstraint(["persona_id"], ["personas.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint(
                "persona_id", "necesidad", name="pk_persona_necesidad_comunidad"
            ),
        )
        op.create_index(
            "ix_persona_necesidades_comunidad_persona_id",
            "persona_necesidades_comunidad",
            ["persona_id"],
        )
        op.create_index(
            "ix_persona_necesidades_comunidad_necesidad",
            "persona_necesidades_comunidad",
            ["necesidad"],
        )


def downgrade() -> None:
    op.drop_index("ix_persona_necesidades_comunidad_necesidad", table_name="persona_necesidades_comunidad")
    op.drop_index("ix_persona_necesidades_comunidad_persona_id", table_name="persona_necesidades_comunidad")
    op.drop_table("persona_necesidades_comunidad")

    op.drop_constraint("persona_longitud_range", "personas", type_="check")
    op.drop_constraint("persona_latitud_range", "personas", type_="check")
    op.drop_constraint("persona_coords_pair", "personas", type_="check")
    op.drop_column("personas", "longitud")
    op.drop_column("personas", "latitud")
    op.drop_column("personas", "entre_calles")
    op.drop_column("personas", "codigo_postal")
    op.drop_column("personas", "colonia")
    op.drop_column("personas", "numero_interior")
    op.drop_column("personas", "numero_exterior")
    op.drop_column("personas", "calle")

    bind = op.get_bind()
    necesidad_comunidad.drop(bind, checkfirst=True)
