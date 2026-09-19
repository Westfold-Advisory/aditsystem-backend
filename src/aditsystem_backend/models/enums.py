from enum import StrEnum


class UserRole(StrEnum):
    # Legacy values — do not reclassify existing rows until PO provides classification
    POLITICO = "POLITICO"
    LIDER = "LIDER"
    INVITADO = "INVITADO"
    ADMIN = "ADMIN"
    # Hierarchy-aware roles (TRA-87)
    GENERAL_COORDINATOR = "GENERAL_COORDINATOR"
    COORDINATOR = "COORDINATOR"
    LINK = "LINK"
    FRIEND = "FRIEND"


class TipoPolitico(StrEnum):
    GENERAL_COORDINATOR = "GENERAL_COORDINATOR"
    COORDINATOR = "COORDINATOR"


class EventStatus(StrEnum):
    BORRADOR = "BORRADOR"
    PUBLICADO = "PUBLICADO"
    EN_CURSO = "EN_CURSO"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"


# Allowed forward transitions per status.
# Despublicar (PUBLICADO → BORRADOR) returns the event to editable draft state.
EVENT_TRANSITIONS: dict["EventStatus", frozenset["EventStatus"]] = {
    EventStatus.BORRADOR: frozenset({EventStatus.PUBLICADO, EventStatus.CANCELADO}),
    EventStatus.PUBLICADO: frozenset(
        {EventStatus.BORRADOR, EventStatus.EN_CURSO, EventStatus.CANCELADO}
    ),
    EventStatus.EN_CURSO: frozenset({EventStatus.FINALIZADO, EventStatus.CANCELADO}),
    EventStatus.FINALIZADO: frozenset(),
    EventStatus.CANCELADO: frozenset(),
}


class InvitationStatus(StrEnum):
    PENDIENTE = "PENDIENTE"
    ACEPTADA = "ACEPTADA"
    RECHAZADA = "RECHAZADA"
    CANCELADA = "CANCELADA"
    EXPIRADA = "EXPIRADA"


class AttendanceStatus(StrEnum):
    INVITADO = "INVITADO"
    CONFIRMADO = "CONFIRMADO"
    PRESENTE = "PRESENTE"
    AUSENTE = "AUSENTE"
    CANCELADO = "CANCELADO"


class CheckinMethod(StrEnum):
    QR = "QR"
    MANUAL = "MANUAL"
    GEOLOCALIZACION = "GEOLOCALIZACION"
    CODIGO = "CODIGO"
    ADMIN = "ADMIN"


class EstatusPersona(StrEnum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"
    BAJA = "BAJA"


class EntityType(StrEnum):
    POLITICO = "POLITICO"
    LIDER = "LIDER"
    INVITADO = "INVITADO"


class DocumentoTipo(StrEnum):
    CV = "CV"
    FOTO = "FOTO"
    IDENTIFICACION = "IDENTIFICACION"
    OTRO = "OTRO"


class TipoGeocerca(StrEnum):
    ESTADO = "ESTADO"
    MUNICIPIO = "MUNICIPIO"
    DISTRITO = "DISTRITO"
