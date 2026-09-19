"""TRA-87: hierarchy roles and parent ownership on politicos

Adds four new values to the user_role enum (additive, PostgreSQL-safe),
introduces the tipo_politico enum type, and extends politicos with:
  - tipo          (tipo_politico, nullable)
  - parent_politico_id (FK → politicos.id, nullable, indexed)
  - CHECK constraint preventing self-parent

Downgrade is safe only when no rows carry the new role/tipo values;
it raises an exception at migration time if they exist.

Revision ID: 20260919_000004
Revises: 20260919_000003
Create Date: 2026-09-19 00:00:04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260919_000004"
down_revision = "20260919_000003"
branch_labels = None
depends_on = None

# New enum values to add to user_role (additive — PostgreSQL has no remove-value DDL)
_NEW_USER_ROLES = ("GENERAL_COORDINATOR", "COORDINATOR", "LINK", "FRIEND")


def upgrade() -> None:
    # 1. Extend user_role with the four hierarchy-aware values (IF NOT EXISTS is safe
    #    on re-run and prevents duplicate-value errors on a partial failure).
    bind = op.get_bind()
    for value in _NEW_USER_ROLES:
        bind.execute(
            sa.text(f"ALTER TYPE user_role ADD VALUE IF NOT EXISTS '{value}'")
        )

    # 2. Create tipo_politico enum
    bind.execute(
        sa.text(
            "CREATE TYPE tipo_politico AS ENUM "
            "('GENERAL_COORDINATOR', 'COORDINATOR')"
        )
    )

    # 3. Add tipo column (nullable — existing rows are unclassified pending PO decision)
    op.add_column(
        "politicos",
        sa.Column(
            "tipo",
            sa.Enum("GENERAL_COORDINATOR", "COORDINATOR", name="tipo_politico", create_type=False),
            nullable=True,
        ),
    )

    # 4. Add parent_politico_id column (nullable FK to self — must be UUID to match politicos.id)
    op.add_column(
        "politicos",
        sa.Column("parent_politico_id", postgresql.UUID(as_uuid=False), nullable=True),
    )

    # 5. FK constraint General → Coordinator ownership
    op.create_foreign_key(
        "fk_politicos_parent_politico_id_politicos",
        "politicos",
        "politicos",
        ["parent_politico_id"],
        ["id"],
    )

    # 6. Index for ownership look-ups
    op.create_index(
        "ix_politicos_parent_politico_id",
        "politicos",
        ["parent_politico_id"],
    )

    # 7. Anti-self-parent constraint
    op.create_check_constraint(
        "ck_politicos_no_self_parent",
        "politicos",
        "parent_politico_id != id",
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Guard: refuse downgrade if any row uses the new tipo or role values
    bind.execute(
        sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM politicos
                WHERE tipo IS NOT NULL
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade TRA-87: rows in politicos have tipo set. '
                    'Clear the tipo and parent_politico_id columns first.';
            END IF;
            IF EXISTS (
                SELECT 1 FROM users
                WHERE role::text IN ('GENERAL_COORDINATOR','COORDINATOR','LINK','FRIEND')
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade TRA-87: rows in users carry new role values. '
                    'Reclassify them to legacy roles before downgrading.';
            END IF;
        END $$
        """)
    )

    # Remove structural additions in reverse order
    op.drop_constraint("ck_politicos_no_self_parent", "politicos", type_="check")
    op.drop_index("ix_politicos_parent_politico_id", table_name="politicos")
    op.drop_constraint(
        "fk_politicos_parent_politico_id_politicos", "politicos", type_="foreignkey"
    )
    op.drop_column("politicos", "parent_politico_id")
    op.drop_column("politicos", "tipo")

    # Drop tipo_politico enum
    bind.execute(sa.text("DROP TYPE tipo_politico"))

    # Revert user_role to the original four values.
    # PostgreSQL has no DROP VALUE; we recreate the type via a rename/replace cycle.
    bind.execute(sa.text("ALTER TYPE user_role RENAME TO user_role_new"))
    bind.execute(
        sa.text(
            "CREATE TYPE user_role AS ENUM ('POLITICO', 'LIDER', 'INVITADO', 'ADMIN')"
        )
    )
    bind.execute(
        sa.text(
            "ALTER TABLE users ALTER COLUMN role "
            "TYPE user_role USING role::text::user_role"
        )
    )
    bind.execute(sa.text("DROP TYPE user_role_new"))
