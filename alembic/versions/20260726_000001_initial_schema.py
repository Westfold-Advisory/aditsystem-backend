"""initial schema

Revision ID: 20260726_000001
Revises:
Create Date: 2026-07-26 00:00:01
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography
from sqlalchemy.dialects import postgresql


revision = "20260726_000001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    user_role = sa.Enum("POLITICO", "LIDER", "INVITADO", "ADMIN", name="user_role")
    event_status = sa.Enum(
        "BORRADOR", "PUBLICADO", "EN_CURSO", "FINALIZADO", "CANCELADO", name="event_status"
    )
    invitation_status = sa.Enum(
        "PENDIENTE", "ACEPTADA", "RECHAZADA", "CANCELADA", "EXPIRADA", name="invitation_status"
    )
    attendance_status = sa.Enum(
        "INVITADO", "CONFIRMADO", "PRESENTE", "AUSENTE", "CANCELADO", name="attendance_status"
    )
    checkin_method = sa.Enum(
        "QR", "MANUAL", "GEOLOCALIZACION", "CODIGO", "ADMIN", name="checkin_method"
    )

    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    event_status.create(bind, checkfirst=True)
    invitation_status.create(bind, checkfirst=True)
    attendance_status.create(bind, checkfirst=True)
    checkin_method.create(bind, checkfirst=True)

    op.create_table(
        "politicos",
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("apellido_paterno", sa.String(length=120), nullable=False),
        sa.Column("apellido_materno", sa.String(length=120), nullable=False),
        sa.Column("telefono", sa.String(length=30), nullable=False),
        sa.Column("perfil_academico", sa.String(length=255), nullable=True),
        sa.Column("equipo", sa.String(length=255), nullable=True),
        sa.Column("enlace", sa.String(length=255), nullable=True),
        sa.Column("municipio", sa.String(length=120), nullable=True),
        sa.Column("distrito", sa.String(length=120), nullable=True),
        sa.Column("seccion", sa.String(length=120), nullable=True),
        sa.Column("direccion", sa.String(length=255), nullable=True),
        sa.Column("latitud", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitud", sa.Numeric(10, 6), nullable=True),
        sa.Column("url_imagen", sa.String(length=500), nullable=True),
        sa.Column("url_cv", sa.String(length=500), nullable=True),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_politicos"),
    )

    op.create_table(
        "lider",
        sa.Column("politico_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("apellido_paterno", sa.String(length=120), nullable=False),
        sa.Column("apellido_materno", sa.String(length=120), nullable=False),
        sa.Column("telefono", sa.String(length=30), nullable=False),
        sa.Column("perfil_academico", sa.String(length=255), nullable=True),
        sa.Column("equipo", sa.String(length=255), nullable=True),
        sa.Column("enlace", sa.String(length=255), nullable=True),
        sa.Column("municipio", sa.String(length=120), nullable=True),
        sa.Column("distrito", sa.String(length=120), nullable=True),
        sa.Column("seccion", sa.String(length=120), nullable=True),
        sa.Column("direccion", sa.String(length=255), nullable=True),
        sa.Column("latitud", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitud", sa.Numeric(10, 6), nullable=True),
        sa.Column("url_mapa", sa.String(length=500), nullable=True),
        sa.Column("url_imagen", sa.String(length=500), nullable=True),
        sa.Column("url_cv", sa.String(length=500), nullable=True),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(["politico_id"], ["politicos.id"], name="fk_lider_politico_id_politicos"),
        sa.PrimaryKeyConstraint("id", name="pk_lider"),
    )
    op.create_index(op.f("ix_lider_politico_id"), "lider", ["politico_id"], unique=False)

    op.create_table(
        "invitados",
        sa.Column("gestor_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("apellido_paterno", sa.String(length=120), nullable=False),
        sa.Column("apellido_materno", sa.String(length=120), nullable=False),
        sa.Column("telefono", sa.String(length=30), nullable=False),
        sa.Column("perfil_academico", sa.String(length=255), nullable=True),
        sa.Column("equipo", sa.String(length=255), nullable=True),
        sa.Column("enlace", sa.String(length=255), nullable=True),
        sa.Column("municipio", sa.String(length=120), nullable=True),
        sa.Column("distrito", sa.String(length=120), nullable=True),
        sa.Column("seccion", sa.String(length=120), nullable=True),
        sa.Column("direccion", sa.String(length=255), nullable=True),
        sa.Column("latitud", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitud", sa.Numeric(10, 6), nullable=True),
        sa.Column("url_mapa", sa.String(length=500), nullable=True),
        sa.Column("url_imagen", sa.String(length=500), nullable=True),
        sa.Column("url_cv", sa.String(length=500), nullable=True),
        sa.Column("estatus", sa.String(length=120), nullable=True),
        sa.Column("fuente_registro", sa.String(length=120), nullable=True),
        sa.Column("codigo_invitacion", sa.String(length=255), nullable=True),
        sa.Column("evento_origen_id", sa.String(length=36), nullable=True),
        sa.Column("asistencias_totales", sa.Integer(), nullable=False),
        sa.Column("ultimo_evento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_registro", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.ForeignKeyConstraint(["gestor_id"], ["lider.id"], name="fk_invitados_gestor_id_lider"),
        sa.PrimaryKeyConstraint("id", name="pk_invitados"),
        sa.UniqueConstraint("codigo_invitacion", name="uq_invitados_codigo_invitacion"),
    )
    op.create_index(op.f("ix_invitados_evento_origen_id"), "invitados", ["evento_origen_id"], unique=False)
    op.create_index(op.f("ix_invitados_gestor_id"), "invitados", ["gestor_id"], unique=False)

    op.create_table(
        "users",
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("politico_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("gestor_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("invitado_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("role", user_role, nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gestor_id"], ["lider.id"], name="fk_users_gestor_id_lider"),
        sa.ForeignKeyConstraint(["invitado_id"], ["invitados.id"], name="fk_users_invitado_id_invitados"),
        sa.ForeignKeyConstraint(["politico_id"], ["politicos.id"], name="fk_users_politico_id_politicos"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("gestor_id", name="uq_users_gestor_id"),
        sa.UniqueConstraint("invitado_id", name="uq_users_invitado_id"),
        sa.UniqueConstraint("politico_id", name="uq_users_politico_id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "events",
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("tipo", sa.String(length=120), nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("latitud", sa.Numeric(9, 6), nullable=False),
        sa.Column("longitud", sa.Numeric(10, 6), nullable=False),
        sa.Column("ubicacion_texto", sa.String(length=255), nullable=False),
        sa.Column("url_mapa", sa.String(length=500), nullable=True),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estatus", event_status, nullable=False),
        sa.Column("capacidad_maxima", sa.Integer(), nullable=True),
        sa.Column("requiere_checkin", sa.Boolean(), nullable=False),
        sa.Column("checkin_abierto_desde", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checkin_abierto_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checkin_radio_metros", sa.Integer(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("ubicacion", Geography("POINT", srid=4326), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("capacidad_maxima IS NULL OR capacidad_maxima > 0", name="ck_events_capacidad_mayor_a_cero"),
        sa.CheckConstraint("checkin_radio_metros IS NULL OR checkin_radio_metros > 0", name="ck_events_radio_mayor_a_cero"),
        sa.CheckConstraint("latitud >= -90 AND latitud <= 90", name="ck_events_latitud_range"),
        sa.CheckConstraint("longitud >= -180 AND longitud <= 180", name="ck_events_longitud_range"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_events_created_by_users"),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
    )
    op.create_index("ix_events_ubicacion", "events", ["ubicacion"], unique=False, postgresql_using="gist")
    op.create_index(op.f("ix_events_created_by"), "events", ["created_by"], unique=False)

    op.create_table(
        "event_invitations",
        sa.Column("evento_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("invitado_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("invitado_por", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("estatus", invitation_status, nullable=False),
        sa.Column("codigo_invitacion", sa.String(length=255), nullable=False),
        sa.Column("fecha_invitacion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fecha_respuesta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["evento_id"], ["events.id"], name="fk_event_invitations_evento_id_events"),
        sa.ForeignKeyConstraint(["invitado_id"], ["invitados.id"], name="fk_event_invitations_invitado_id_invitados"),
        sa.ForeignKeyConstraint(["invitado_por"], ["users.id"], name="fk_event_invitations_invitado_por_users"),
        sa.PrimaryKeyConstraint("id", name="pk_event_invitations"),
        sa.UniqueConstraint("codigo_invitacion", name="uq_event_invitation_code"),
        sa.UniqueConstraint("evento_id", "invitado_id", name="uq_event_invitation_event_invitado"),
    )
    op.create_index(op.f("ix_event_invitations_evento_id"), "event_invitations", ["evento_id"], unique=False)
    op.create_index(op.f("ix_event_invitations_invitado_id"), "event_invitations", ["invitado_id"], unique=False)

    op.create_table(
        "event_attendances",
        sa.Column("evento_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("invitado_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("invitacion_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("estatus", attendance_status, nullable=False),
        sa.Column("checkin_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checkout_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checkin_metodo", checkin_method, nullable=True),
        sa.Column("checkin_latitud", sa.Numeric(9, 6), nullable=True),
        sa.Column("checkin_longitud", sa.Numeric(10, 6), nullable=True),
        sa.Column("distancia_evento_metros", sa.Numeric(10, 2), nullable=True),
        sa.Column("registrado_por", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("dispositivo_id", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["evento_id"], ["events.id"], name="fk_event_attendances_evento_id_events"),
        sa.ForeignKeyConstraint(["invitacion_id"], ["event_invitations.id"], name="fk_event_attendances_invitacion_id_event_invitations"),
        sa.ForeignKeyConstraint(["invitado_id"], ["invitados.id"], name="fk_event_attendances_invitado_id_invitados"),
        sa.ForeignKeyConstraint(["registrado_por"], ["users.id"], name="fk_event_attendances_registrado_por_users"),
        sa.PrimaryKeyConstraint("id", name="pk_event_attendances"),
        sa.UniqueConstraint("evento_id", "invitado_id", name="uq_event_attendance_event_invitado"),
        sa.UniqueConstraint("invitacion_id"),
    )
    op.create_index(op.f("ix_event_attendances_evento_id"), "event_attendances", ["evento_id"], unique=False)
    op.create_index(op.f("ix_event_attendances_invitado_id"), "event_attendances", ["invitado_id"], unique=False)

    op.create_table(
        "event_checkin_tokens",
        sa.Column("event_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("jti", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_event_checkin_tokens_created_by_users"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"], name="fk_event_checkin_tokens_event_id_events"),
        sa.PrimaryKeyConstraint("id", name="pk_event_checkin_tokens"),
        sa.UniqueConstraint("jti", name="uq_event_checkin_token_jti"),
    )
    op.create_index(op.f("ix_event_checkin_tokens_event_id"), "event_checkin_tokens", ["event_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_event_checkin_tokens_event_id"), table_name="event_checkin_tokens")
    op.drop_table("event_checkin_tokens")
    op.drop_index(op.f("ix_event_attendances_invitado_id"), table_name="event_attendances")
    op.drop_index(op.f("ix_event_attendances_evento_id"), table_name="event_attendances")
    op.drop_table("event_attendances")
    op.drop_index(op.f("ix_event_invitations_invitado_id"), table_name="event_invitations")
    op.drop_index(op.f("ix_event_invitations_evento_id"), table_name="event_invitations")
    op.drop_table("event_invitations")
    op.drop_index(op.f("ix_events_created_by"), table_name="events")
    op.drop_index("ix_events_ubicacion", table_name="events")
    op.drop_table("events")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_invitados_gestor_id"), table_name="invitados")
    op.drop_index(op.f("ix_invitados_evento_origen_id"), table_name="invitados")
    op.drop_table("invitados")
    op.drop_index(op.f("ix_lider_politico_id"), table_name="lider")
    op.drop_table("lider")
    op.drop_table("politicos")

    bind = op.get_bind()
    sa.Enum(name="checkin_method").drop(bind, checkfirst=True)
    sa.Enum(name="attendance_status").drop(bind, checkfirst=True)
    sa.Enum(name="invitation_status").drop(bind, checkfirst=True)
    sa.Enum(name="event_status").drop(bind, checkfirst=True)
    sa.Enum(name="user_role").drop(bind, checkfirst=True)
