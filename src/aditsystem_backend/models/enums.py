from enum import StrEnum


class UserRole(StrEnum):
    POLITICO = "POLITICO"
    GESTOR = "GESTOR"
    INVITADO = "INVITADO"
    ADMIN = "ADMIN"


class EventStatus(StrEnum):
    BORRADOR = "BORRADOR"
    PUBLICADO = "PUBLICADO"
    EN_CURSO = "EN_CURSO"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"


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
