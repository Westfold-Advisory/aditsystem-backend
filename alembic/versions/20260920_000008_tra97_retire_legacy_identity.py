"""TRA-97: retire legacy identity tables and columns from the final schema.

This is intentionally a reset-only migration. It refuses populated legacy
tables instead of guessing a Persona mapping; use the guarded local reset or
the approved remote-development procedure before upgrading.
"""

from alembic import op


revision = "20260920_000008"
down_revision = "20260920_000007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE table_name text;
        DECLARE has_rows boolean;
        BEGIN
          FOREACH table_name IN ARRAY ARRAY[
            'users', 'politicos', 'lider', 'invitados', 'documentos', 'events',
            'event_invitations', 'event_attendances', 'event_checkin_tokens'
          ] LOOP
            EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I LIMIT 1)', table_name)
              INTO has_rows;
            IF has_rows THEN
              RAISE EXCEPTION 'TRA-97 requires an empty database; table % contains data', table_name;
            END IF;
          END LOOP;
        END $$;
        """
    )

    op.drop_constraint(
        "fk_documentos_subido_por_users", "documentos", type_="foreignkey"
    )
    op.drop_index("ix_documentos_entity_id", table_name="documentos")
    op.drop_index("ix_documentos_entity_type", table_name="documentos")
    op.drop_column("documentos", "subido_por")
    op.drop_column("documentos", "entity_id")
    op.drop_column("documentos", "entity_type")
    op.alter_column("documentos", "persona_id", nullable=False)
    op.alter_column("documentos", "subido_por_persona_id", nullable=False)

    op.drop_constraint("fk_events_created_by_users", "events", type_="foreignkey")
    op.drop_index("ix_events_created_by", table_name="events")
    op.drop_column("events", "created_by")
    op.alter_column("events", "created_by_persona_id", nullable=False)

    op.drop_constraint(
        "uq_event_invitation_event_invitado", "event_invitations", type_="unique"
    )
    op.drop_constraint(
        "fk_event_invitations_invitado_id_invitados",
        "event_invitations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_event_invitations_invitado_por_users",
        "event_invitations",
        type_="foreignkey",
    )
    op.drop_index("ix_event_invitations_invitado_id", table_name="event_invitations")
    op.drop_column("event_invitations", "invitado_id")
    op.drop_column("event_invitations", "invitado_por")
    op.alter_column("event_invitations", "persona_id", nullable=False)
    op.alter_column("event_invitations", "invitado_por_persona_id", nullable=False)

    op.drop_constraint(
        "uq_event_attendance_event_invitado", "event_attendances", type_="unique"
    )
    op.drop_constraint(
        "fk_event_attendances_invitado_id_invitados",
        "event_attendances",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_event_attendances_registrado_por_users",
        "event_attendances",
        type_="foreignkey",
    )
    op.drop_index("ix_event_attendances_invitado_id", table_name="event_attendances")
    op.drop_column("event_attendances", "invitado_id")
    op.drop_column("event_attendances", "registrado_por")
    op.alter_column("event_attendances", "persona_id", nullable=False)

    op.drop_constraint(
        "fk_event_checkin_tokens_created_by_users",
        "event_checkin_tokens",
        type_="foreignkey",
    )
    op.drop_column("event_checkin_tokens", "created_by")
    op.alter_column("event_checkin_tokens", "created_by_persona_id", nullable=False)

    op.drop_table("users")
    op.drop_table("invitados")
    op.drop_table("lider")
    op.drop_table("politicos")
    op.execute("DROP TYPE IF EXISTS user_role")
    op.execute("DROP TYPE IF EXISTS tipo_politico")
    op.execute("DROP TYPE IF EXISTS entity_type")


def downgrade() -> None:
    raise RuntimeError(
        "TRA-97 is reset-only; recover through a snapshot and previous image."
    )
