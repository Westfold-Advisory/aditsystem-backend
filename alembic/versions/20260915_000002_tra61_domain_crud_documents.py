"""TRA-61: domain CRUD timestamps, status, and versioned documents

Revision ID: 20260915_000002
Revises: 20260726_000001
Create Date: 2026-09-15 00:00:02
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260915_000002"
down_revision = "20260726_000001"
branch_labels = None
depends_on = None

entity_type = sa.Enum("POLITICO", "LIDER", "INVITADO", name="entity_type")
documento_tipo = sa.Enum("CV", "FOTO", "IDENTIFICACION", "OTRO", name="documento_tipo")


def upgrade() -> None:
    # --- politicos: add timestamps, soft-delete, estatus ---
    op.add_column("politicos", sa.Column("estatus", sa.String(length=60), nullable=True))
    op.add_column(
        "politicos",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.add_column(
        "politicos",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.add_column("politicos", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # --- lider: add timestamps, soft-delete, estatus ---
    op.add_column("lider", sa.Column("estatus", sa.String(length=60), nullable=True))
    op.add_column(
        "lider",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.add_column(
        "lider",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.add_column("lider", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # --- invitados: add timestamps, soft-delete ---
    op.add_column(
        "invitados",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.add_column(
        "invitados",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.add_column("invitados", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))

    # --- documentos: new table for versioned metadata ---
    op.create_table(
        "documentos",
        sa.Column("entity_type", entity_type, nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=False),
        sa.Column("tipo", documento_tipo, nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("s3_key", sa.String(length=1000), nullable=False),
        sa.Column("mime_type", sa.String(length=127), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("subido_por", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["subido_por"], ["users.id"], name="fk_documentos_subido_por_users"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_documentos"),
    )
    op.create_index(op.f("ix_documentos_entity_type"), "documentos", ["entity_type"], unique=False)
    op.create_index(op.f("ix_documentos_entity_id"), "documentos", ["entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_documentos_entity_id"), table_name="documentos")
    op.drop_index(op.f("ix_documentos_entity_type"), table_name="documentos")
    op.drop_table("documentos")

    bind = op.get_bind()
    documento_tipo.drop(bind, checkfirst=True)
    entity_type.drop(bind, checkfirst=True)

    op.drop_column("invitados", "deleted_at")
    op.drop_column("invitados", "updated_at")
    op.drop_column("invitados", "created_at")

    op.drop_column("lider", "deleted_at")
    op.drop_column("lider", "updated_at")
    op.drop_column("lider", "created_at")
    op.drop_column("lider", "estatus")

    op.drop_column("politicos", "deleted_at")
    op.drop_column("politicos", "updated_at")
    op.drop_column("politicos", "created_at")
    op.drop_column("politicos", "estatus")
