"""rename gestor to lider

Revision ID: 20260914_000001
Revises: 20260726_000001
Create Date: 2026-09-14 00:00:01

Renames the GESTOR role and gestor concept to LIDER throughout the schema:
- user_role enum: GESTOR → LIDER
- table: gestores → lideres
- column: invitados.gestor_id → invitados.lider_id
- column: users.gestor_id → users.lider_id
- foreign keys, unique constraints, and indexes renamed to match

Downgrade: reverses all changes above; safe on a pre-migration DB.
"""

from alembic import op
import sqlalchemy as sa

revision = "20260914_000001"
down_revision = "20260726_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Rename enum value GESTOR → LIDER
    bind.execute(sa.text("ALTER TYPE user_role RENAME VALUE 'GESTOR' TO 'LIDER'"))

    # 2. Rename table gestores → lideres (includes its PK implicitly)
    op.rename_table("gestores", "lideres")

    # 3. Rename PK constraint on lideres
    op.execute("ALTER TABLE lideres RENAME CONSTRAINT pk_gestores TO pk_lideres")

    # 4. Rename FK on lideres (politico_id -> politicos.id)
    op.execute(
        "ALTER TABLE lideres RENAME CONSTRAINT fk_gestores_politico_id_politicos "
        "TO fk_lideres_politico_id_politicos"
    )

    # 5. Rename index on lideres.politico_id
    op.execute("ALTER INDEX ix_gestores_politico_id RENAME TO ix_lideres_politico_id")

    # 6. Rename column invitados.gestor_id → invitados.lider_id
    op.alter_column("invitados", "gestor_id", new_column_name="lider_id")

    # 7. Rename FK on invitados.lider_id
    op.execute(
        "ALTER TABLE invitados RENAME CONSTRAINT fk_invitados_gestor_id_gestores "
        "TO fk_invitados_lider_id_lideres"
    )

    # 8. Rename index on invitados.lider_id
    op.execute("ALTER INDEX ix_invitados_gestor_id RENAME TO ix_invitados_lider_id")

    # 9. Rename column users.gestor_id → users.lider_id
    op.alter_column("users", "gestor_id", new_column_name="lider_id")

    # 10. Rename FK on users.lider_id
    op.execute(
        "ALTER TABLE users RENAME CONSTRAINT fk_users_gestor_id_gestores "
        "TO fk_users_lider_id_lideres"
    )

    # 11. Rename unique constraint on users.lider_id
    op.execute(
        "ALTER TABLE users RENAME CONSTRAINT uq_users_gestor_id TO uq_users_lider_id"
    )


def downgrade() -> None:
    bind = op.get_bind()

    # 11. Restore unique constraint name on users
    op.execute(
        "ALTER TABLE users RENAME CONSTRAINT uq_users_lider_id TO uq_users_gestor_id"
    )

    # 10. Restore FK name on users
    op.execute(
        "ALTER TABLE users RENAME CONSTRAINT fk_users_lider_id_lideres "
        "TO fk_users_gestor_id_gestores"
    )

    # 9. Restore column users.lider_id → users.gestor_id
    op.alter_column("users", "lider_id", new_column_name="gestor_id")

    # 8. Restore index name on invitados
    op.execute("ALTER INDEX ix_invitados_lider_id RENAME TO ix_invitados_gestor_id")

    # 7. Restore FK name on invitados
    op.execute(
        "ALTER TABLE invitados RENAME CONSTRAINT fk_invitados_lider_id_lideres "
        "TO fk_invitados_gestor_id_gestores"
    )

    # 6. Restore column invitados.lider_id → invitados.gestor_id
    op.alter_column("invitados", "lider_id", new_column_name="gestor_id")

    # 5. Restore index name on lideres
    op.execute("ALTER INDEX ix_lideres_politico_id RENAME TO ix_gestores_politico_id")

    # 4. Restore FK name on lideres
    op.execute(
        "ALTER TABLE lideres RENAME CONSTRAINT fk_lideres_politico_id_politicos "
        "TO fk_gestores_politico_id_politicos"
    )

    # 3. Restore PK name on lideres
    op.execute("ALTER TABLE lideres RENAME CONSTRAINT pk_lideres TO pk_gestores")

    # 2. Restore table name lideres → gestores
    op.rename_table("lideres", "gestores")

    # 1. Restore enum value LIDER → GESTOR
    bind.execute(sa.text("ALTER TYPE user_role RENAME VALUE 'LIDER' TO 'GESTOR'"))
