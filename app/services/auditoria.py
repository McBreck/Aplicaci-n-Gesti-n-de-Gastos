"""AuditoriaService: bitácora de eventos (RNF-12, OWASP A09).

El evento se agrega a la sesión de base de datos y se guarda con el mismo
commit de la operación auditada. Nunca se registran contraseñas.
"""
from flask import has_request_context, request

from app.extensions import db
from app.models import Auditoria

INICIO_SESION = "INICIO_SESION"
CIERRE_SESION = "CIERRE_SESION"
LOGIN_FALLIDO = "LOGIN_FALLIDO"
CREAR = "CREAR"
MODIFICAR = "MODIFICAR"
ELIMINAR = "ELIMINAR"
ACTIVAR = "ACTIVAR"
DESACTIVAR = "DESACTIVAR"
RESTABLECER = "RESTABLECER"

_CLAVES_SENSIBLES = ("contrasena", "contraseña", "password", "clave")


def _sin_datos_sensibles(valor):
    if isinstance(valor, dict):
        return {
            clave: _sin_datos_sensibles(contenido)
            for clave, contenido in valor.items()
            if not any(sensible in clave.lower() for sensible in _CLAVES_SENSIBLES)
        }
    if isinstance(valor, list):
        return [_sin_datos_sensibles(elemento) for elemento in valor]
    return valor


def registrar(
    accion: str,
    entidad: str,
    *,
    usuario_id: int | None = None,
    entidad_id: int | None = None,
    detalle: dict | None = None,
) -> Auditoria:
    """Agrega un evento con la IP de la petición actual (sin hacer commit)."""
    evento = Auditoria(
        accion=accion,
        entidad=entidad,
        usuario_id=usuario_id,
        entidad_id=entidad_id,
        detalle=_sin_datos_sensibles(detalle) if detalle else None,
        ip=request.remote_addr if has_request_context() else None,
    )
    db.session.add(evento)
    return evento
