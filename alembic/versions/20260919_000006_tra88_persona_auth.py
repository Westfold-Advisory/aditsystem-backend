"""TRA-88 final persona/auth persistence foundation.

Revision ID: 20260919_000006
Revises: 20260919_000005
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260919_000006"
down_revision = "20260919_000005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    person_role = sa.Enum(
        "ADMIN", "COORDINADOR_GENERAL", "COORDINADOR", "ENLACE", "AMIGO", name="person_role"
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
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["parent_persona_id"], ["personas.id"]),
        sa.CheckConstraint("parent_persona_id IS NULL OR parent_persona_id != id", name="no_self_parent"),
    )
    op.create_index("ix_personas_parent_persona_id", "personas", ["parent_persona_id"])
    op.create_index("ix_personas_rol", "personas", ["rol"])
    op.create_table(
        "auth_users",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("persona_id", postgresql.UUID(as_uuid=False), nullable=False, unique=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["persona_id"], ["personas.id"]),
    )
    op.execute("""
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
    op.execute("DROP FUNCTION IF EXISTS reject_amigo_auth_user() CASCADE")
    op.drop_table("auth_users")
    op.drop_index("ix_personas_rol", table_name="personas")
    op.drop_index("ix_personas_parent_persona_id", table_name="personas")
    op.drop_table("personas")
