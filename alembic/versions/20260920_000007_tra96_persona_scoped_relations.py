"""TRA-96: add Persona ownership to documents and event records.

The legacy identifiers are intentionally retained during this release.  They
are needed to read existing rows while the application backfills Persona
links.  New writes must populate the Persona columns; the next destructive
legacy-retirement migration is only safe once the audit query below returns
zero rows.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260920_000007"
down_revision = "20260919_000006"
branch_labels = None
depends_on = None


def _uuid_column(name: str) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=False), nullable=True)


def upgrade() -> None:
    op.execute("ALTER TYPE entity_type ADD VALUE IF NOT EXISTS 'PERSONA'")
    # These columns establish the business ownership boundary.  They stay
    # nullable only for pre-TRA-96 records, whose legacy entities cannot be
    # unambiguously mapped to Persona without an operator-approved mapping.
    for table, column in (
        ("documentos", "persona_id"),
        ("documentos", "subido_por_persona_id"),
        ("events", "created_by_persona_id"),
        ("event_invitations", "persona_id"),
        ("event_invitations", "invitado_por_persona_id"),
        ("event_attendances", "persona_id"),
        ("event_attendances", "registrado_por_persona_id"),
        ("event_checkin_tokens", "created_by_persona_id"),
    ):
        op.add_column(table, _uuid_column(column))
        op.create_foreign_key(
            f"fk_{table}_{column}_personas", table, "personas", [column], ["id"]
        )
        op.create_index(f"ix_{table}_{column}", table, [column])

    # New Persona-scoped documents do not have a legacy users row.
    op.alter_column("documentos", "subido_por", existing_type=postgresql.UUID(as_uuid=False), nullable=True)
    for table, column in (
        ("events", "created_by"),
        ("event_invitations", "invitado_id"),
        ("event_invitations", "invitado_por"),
        ("event_attendances", "invitado_id"),
        ("event_checkin_tokens", "created_by"),
    ):
        op.alter_column(table, column, existing_type=postgresql.UUID(as_uuid=False), nullable=True)

    # AuthUser → Persona is the only lossless legacy identity mapping.
    # Backfill author/auditor fields where that mapping exists.  Invitation
    # recipients and document subjects are deliberately not guessed.
    op.execute("""
        UPDATE events e SET created_by_persona_id = au.persona_id
        FROM users u JOIN auth_users au ON lower(au.email) = lower(u.email)
        WHERE e.created_by = u.id AND e.created_by_persona_id IS NULL
    """)
    op.execute("""
        UPDATE documentos d SET subido_por_persona_id = au.persona_id
        FROM users u JOIN auth_users au ON lower(au.email) = lower(u.email)
        WHERE d.subido_por = u.id AND d.subido_por_persona_id IS NULL
    """)
    op.execute("""
        UPDATE event_invitations i SET invitado_por_persona_id = au.persona_id
        FROM users u JOIN auth_users au ON lower(au.email) = lower(u.email)
        WHERE i.invitado_por = u.id AND i.invitado_por_persona_id IS NULL
    """)
    op.execute("""
        UPDATE event_attendances a SET registrado_por_persona_id = au.persona_id
        FROM users u JOIN auth_users au ON lower(au.email) = lower(u.email)
        WHERE a.registrado_por = u.id AND a.registrado_por_persona_id IS NULL
    """)
    op.execute("""
        UPDATE event_checkin_tokens t SET created_by_persona_id = au.persona_id
        FROM users u JOIN auth_users au ON lower(au.email) = lower(u.email)
        WHERE t.created_by = u.id AND t.created_by_persona_id IS NULL
    """)
    op.create_unique_constraint("uq_event_invitation_event_persona", "event_invitations", ["evento_id", "persona_id"])
    op.create_unique_constraint("uq_event_attendance_event_persona", "event_attendances", ["evento_id", "persona_id"])


def downgrade() -> None:
    # PostgreSQL cannot safely remove an enum value in-place.  The retained
    # value is harmless after rolling back the relation columns.
    op.drop_constraint("uq_event_attendance_event_persona", "event_attendances", type_="unique")
    op.drop_constraint("uq_event_invitation_event_persona", "event_invitations", type_="unique")
    op.alter_column("documentos", "subido_por", existing_type=postgresql.UUID(as_uuid=False), nullable=False)
    for table, column in reversed((
        ("documentos", "persona_id"),
        ("documentos", "subido_por_persona_id"),
        ("events", "created_by_persona_id"),
        ("event_invitations", "persona_id"),
        ("event_invitations", "invitado_por_persona_id"),
        ("event_attendances", "persona_id"),
        ("event_attendances", "registrado_por_persona_id"),
        ("event_checkin_tokens", "created_by_persona_id"),
    )):
        op.drop_index(f"ix_{table}_{column}", table_name=table)
        op.drop_constraint(f"fk_{table}_{column}_personas", table, type_="foreignkey")
        op.drop_column(table, column)
