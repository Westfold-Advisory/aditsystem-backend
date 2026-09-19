"""TRA-88 final persona/auth persistence foundation.

Revision ID: 20260919_000006
Revises: 20260919_000005
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260919_000006"
down_revision = "20260919_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    person_role = postgresql.ENUM(
        "ADMIN",
        "COORDINADOR_GENERAL",
        "COORDINADOR",
        "ENLACE",
        "AMIGO",
        name="person_role",
        create_type=False,
    )
    person_role.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "personas",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("rol", person_role, nullable=False),
        sa.Column("parent_persona_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("apellido_paterno", sa.String(120), nullable=False),
        sa.Column("apellido_materno", sa.String(120), nullable=False),
        sa.Column("telefono", sa.String(30), nullable=False),
        sa.Column("estatus", sa.String(30), nullable=False, server_default="ACTIVO"),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), nullable=False),
        sa.Column("perfil_academico", sa.String(255), nullable=True),
        sa.Column("equipo", sa.String(255), nullable=True),
        sa.Column("contacto", sa.String(255), nullable=True),
        sa.Column("seccion", sa.String(120), nullable=True),
        sa.Column("direccion", sa.String(255), nullable=True),
        sa.Column("latitud", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitud", sa.Numeric(10, 6), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["parent_persona_id"], ["personas.id"]),
        sa.CheckConstraint(
            "parent_persona_id IS NULL OR parent_persona_id != id",
            name="no_self_parent",
        ),
        sa.CheckConstraint(
            "latitud IS NULL OR (latitud >= -90 AND latitud <= 90)",
            name="latitud_range",
        ),
        sa.CheckConstraint(
            "longitud IS NULL OR (longitud >= -180 AND longitud <= 180)",
            name="longitud_range",
        ),
    )
    op.create_index("ix_personas_parent_persona_id", "personas", ["parent_persona_id"])
    op.create_index("ix_personas_rol", "personas", ["rol"])
    op.create_table(
        "auth_users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "persona_id", postgresql.UUID(as_uuid=False), nullable=False, unique=True
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
    )
    op.execute("""
    CREATE FUNCTION validate_persona_hierarchy() RETURNS trigger AS $$
    DECLARE
      parent_role person_role;
      parent_deleted_at timestamptz;
    BEGIN
      IF NEW.rol IN ('ADMIN', 'COORDINADOR_GENERAL') THEN
        IF NEW.parent_persona_id IS NOT NULL THEN
          RAISE EXCEPTION '% debe ser raíz del árbol', NEW.rol;
        END IF;
      ELSE
        IF NEW.parent_persona_id IS NULL THEN
          RAISE EXCEPTION '% requiere una persona padre', NEW.rol;
        END IF;

        SELECT rol, deleted_at INTO parent_role, parent_deleted_at
        FROM personas WHERE id = NEW.parent_persona_id;
        IF NOT FOUND THEN
          RAISE EXCEPTION 'la persona padre no existe';
        END IF;
        IF parent_deleted_at IS NOT NULL THEN
          RAISE EXCEPTION 'la persona padre está dada de baja';
        END IF;
        IF (NEW.rol = 'COORDINADOR' AND parent_role <> 'COORDINADOR_GENERAL')
          OR (NEW.rol = 'ENLACE' AND parent_role <> 'COORDINADOR')
          OR (NEW.rol = 'AMIGO' AND parent_role <> 'ENLACE') THEN
          RAISE EXCEPTION 'relación jerárquica inválida: % no puede depender de %', NEW.rol, parent_role;
        END IF;
      END IF;

      IF NEW.rol = 'AMIGO' AND EXISTS (
        SELECT 1 FROM auth_users WHERE persona_id = NEW.id
      ) THEN
        RAISE EXCEPTION 'AMIGO no puede tener cuenta autenticable';
      END IF;
      IF EXISTS (
        SELECT 1 FROM personas child
        WHERE child.parent_persona_id = NEW.id
          AND child.deleted_at IS NULL
          AND NOT (
            (child.rol = 'COORDINADOR' AND NEW.rol = 'COORDINADOR_GENERAL')
            OR (child.rol = 'ENLACE' AND NEW.rol = 'COORDINADOR')
            OR (child.rol = 'AMIGO' AND NEW.rol = 'ENLACE')
          )
      ) THEN
        RAISE EXCEPTION 'el cambio deja descendientes con una relación inválida';
      END IF;
      IF NEW.deleted_at IS NOT NULL AND EXISTS (
        SELECT 1 FROM personas child
        WHERE child.parent_persona_id = NEW.id AND child.deleted_at IS NULL
      ) THEN
        RAISE EXCEPTION 'no se puede dar de baja una persona con descendientes activos';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    CREATE TRIGGER trg_persona_hierarchy
    BEFORE INSERT OR UPDATE OF rol, parent_persona_id, deleted_at ON personas
    FOR EACH ROW EXECUTE FUNCTION validate_persona_hierarchy();

    CREATE FUNCTION reject_amigo_auth_user() RETURNS trigger AS $$
    BEGIN
      IF EXISTS (SELECT 1 FROM personas WHERE id = NEW.persona_id AND rol = 'AMIGO') THEN
        RAISE EXCEPTION 'AMIGO no puede tener cuenta autenticable';
      END IF;
      RETURN NEW;
    END; $$ LANGUAGE plpgsql;
    CREATE TRIGGER trg_auth_user_not_amigo BEFORE INSERT OR UPDATE OF persona_id ON auth_users
    FOR EACH ROW EXECUTE FUNCTION reject_amigo_auth_user();
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS validate_persona_hierarchy() CASCADE")
    op.execute("DROP FUNCTION IF EXISTS reject_amigo_auth_user() CASCADE")
    op.drop_table("auth_users")
    op.drop_index("ix_personas_rol", table_name="personas")
    op.drop_index("ix_personas_parent_persona_id", table_name="personas")
    op.drop_table("personas")
