"""TRA-87: drop legacy user_role values and remap existing rows

Remaps the three legacy role labels to their hierarchy equivalents:
  POLITICO  → COORDINATOR  (was the direct owner of LINKs)
  LIDER     → LINK
  INVITADO  → FRIEND

Then rebuilds the user_role enum with only the five canonical values:
  ADMIN, GENERAL_COORDINATOR, COORDINATOR, LINK, FRIEND

Downgrade restores the eight-value enum from migration 000004 and maps back:
  COORDINATOR → POLITICO  (loses GENERAL_COORDINATOR granularity; guarded)
  LINK        → LIDER
  FRIEND      → INVITADO

Revision ID: 20260919_000005
Revises: 20260919_000004
Create Date: 2026-09-19 00:00:05
"""

import sqlalchemy as sa
from alembic import op

revision = "20260919_000005"
down_revision = "20260919_000004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Detach column from enum so we can rebuild the type
    bind.execute(sa.text(
        "ALTER TABLE users ALTER COLUMN role TYPE text USING role::text"
    ))

    # 2. Remap legacy values
    bind.execute(sa.text("UPDATE users SET role = 'COORDINATOR' WHERE role = 'POLITICO'"))
    bind.execute(sa.text("UPDATE users SET role = 'LINK'        WHERE role = 'LIDER'"))
    bind.execute(sa.text("UPDATE users SET role = 'FRIEND'      WHERE role = 'INVITADO'"))

    # 3. Drop the eight-value enum created by migrations 000001 + 000004
    bind.execute(sa.text("DROP TYPE user_role"))

    # 4. Create canonical five-value enum
    bind.execute(sa.text(
        "CREATE TYPE user_role AS ENUM "
        "('ADMIN', 'GENERAL_COORDINATOR', 'COORDINATOR', 'LINK', 'FRIEND')"
    ))

    # 5. Restore column type
    bind.execute(sa.text(
        "ALTER TABLE users ALTER COLUMN role "
        "TYPE user_role USING role::user_role"
    ))


def downgrade() -> None:
    bind = op.get_bind()

    # Guard: GENERAL_COORDINATOR has no legacy equivalent
    bind.execute(sa.text("""
        DO $$ BEGIN
            IF EXISTS (
                SELECT 1 FROM users WHERE role::text = 'GENERAL_COORDINATOR'
            ) THEN
                RAISE EXCEPTION
                    'Cannot downgrade TRA-87 step 5: GENERAL_COORDINATOR rows exist '
                    'with no legacy equivalent. Reclassify them first.';
            END IF;
        END $$
    """))

    # 1. Detach column
    bind.execute(sa.text(
        "ALTER TABLE users ALTER COLUMN role TYPE text USING role::text"
    ))

    # 2. Reverse remap
    bind.execute(sa.text("UPDATE users SET role = 'POLITICO'  WHERE role = 'COORDINATOR'"))
    bind.execute(sa.text("UPDATE users SET role = 'LIDER'     WHERE role = 'LINK'"))
    bind.execute(sa.text("UPDATE users SET role = 'INVITADO'  WHERE role = 'FRIEND'"))

    # 3. Drop canonical enum
    bind.execute(sa.text("DROP TYPE user_role"))

    # 4. Restore the eight-value enum (state after migration 000004)
    bind.execute(sa.text(
        "CREATE TYPE user_role AS ENUM ("
        "'POLITICO', 'LIDER', 'INVITADO', 'ADMIN', "
        "'GENERAL_COORDINATOR', 'COORDINATOR', 'LINK', 'FRIEND')"
    ))

    # 5. Restore column type
    bind.execute(sa.text(
        "ALTER TABLE users ALTER COLUMN role "
        "TYPE user_role USING role::user_role"
    ))
