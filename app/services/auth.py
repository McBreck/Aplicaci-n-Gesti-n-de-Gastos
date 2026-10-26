"""AuthService: inicio de sesión, bloqueo por intentos fallidos y cambio de contraseña.

Requisitos: RF-01 a RF-03, RNF-11 (bloqueo de 15 minutos tras 5 intentos).
"""
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.extensions import db
from app.models import Usuario
from app.services import auditoria
from app.services.formato import ahora_lima
from app.services.usuario import ENTIDAD, ErrorUsuario, buscar_por_correo, validar_contrasena

MAXIMO_INTENTOS = 5
DURACION_BLOQUEO = timedelta(minutes=15)
MENSAJE_CREDENCIALES = "Correo o contraseña incorrectos."
MENSAJE_DESACTIVADA = "Tu cuenta está desactivada. Comunícate con el administrador."


@dataclass(frozen=True)
class ResultadoAutenticacion:
    usuario: Usuario | None = None
    error: str | None = None

    @property
    def exitoso(self) -> bool:
        return self.usuario is not None


@cache
def _hash_ficticio() -> str:
    return PasswordHasher().hash("contrasena-ficticia-1")


def _verificar_contrasena_ficticia(contrasena: str) -> None:
    """Un correo inexistente tarda lo mismo que uno real (evita adivinar cuentas)."""
    try:
        PasswordHasher().verify(_hash_ficticio(), contrasena)
    except VerificationError:
        pass


def esta_bloqueado(usuario: Usuario) -> bool:
    return usuario.bloqueado_hasta is not None and usuario.bloqueado_hasta > ahora_lima()


def mensaje_bloqueo(bloqueado_hasta: datetime) -> str:
    minutos = max(1, math.ceil((bloqueado_hasta - ahora_lima()).total_seconds() / 60))
    unidad = "minuto" if minutos == 1 else "minutos"
    return f"Por seguridad, tu cuenta está bloqueada. Inténtalo de nuevo en {minutos} {unidad}."


def _registrar_fallo(usuario: Usuario | None, motivo: str, correo: str | None = None) -> None:
    detalle = {"motivo": motivo}
    if usuario is None:
        detalle["correo"] = correo
    auditoria.registrar(
        auditoria.LOGIN_FALLIDO,
        ENTIDAD,
        usuario_id=usuario.id if usuario else None,
        entidad_id=usuario.id if usuario else None,
        detalle=detalle,
    )


def _contar_intento_fallido(usuario: Usuario) -> str:
    usuario.intentos_fallidos += 1
    if usuario.intentos_fallidos >= MAXIMO_INTENTOS:
        usuario.intentos_fallidos = 0
        usuario.bloqueado_hasta = ahora_lima() + DURACION_BLOQUEO
        _registrar_fallo(usuario, "bloqueo_por_intentos")
        return mensaje_bloqueo(usuario.bloqueado_hasta)
    _registrar_fallo(usuario, "contrasena_incorrecta")
    return MENSAJE_CREDENCIALES


def _registrar_acceso(usuario: Usuario, contrasena: str) -> None:
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    usuario.ultimo_acceso = ahora_lima()
    if usuario.necesita_rehash():
        usuario.establecer_contrasena(contrasena)
    auditoria.registrar(auditoria.INICIO_SESION, ENTIDAD, usuario_id=usuario.id, entidad_id=usuario.id)


def autenticar(correo: str, contrasena: str) -> ResultadoAutenticacion:
    """CU-01 con sus flujos alternos 4b (bloqueo) y 4c (cuenta desactivada)."""
    usuario = buscar_por_correo(correo)
    if usuario is None:
        _verificar_contrasena_ficticia(contrasena)
        _registrar_fallo(None, "correo_no_registrado", correo=(correo or "").strip()[:120])
        resultado = ResultadoAutenticacion(error=MENSAJE_CREDENCIALES)
    elif esta_bloqueado(usuario):
        _registrar_fallo(usuario, "cuenta_bloqueada")
        resultado = ResultadoAutenticacion(error=mensaje_bloqueo(usuario.bloqueado_hasta))
    elif not usuario.verificar_contrasena(contrasena):
        resultado = ResultadoAutenticacion(error=_contar_intento_fallido(usuario))
    elif not usuario.activo:
        _registrar_fallo(usuario, "cuenta_desactivada")
        resultado = ResultadoAutenticacion(error=MENSAJE_DESACTIVADA)
    else:
        _registrar_acceso(usuario, contrasena)
        resultado = ResultadoAutenticacion(usuario=usuario)
    db.session.commit()
    return resultado


def registrar_cierre_sesion(usuario: Usuario) -> None:
    auditoria.registrar(auditoria.CIERRE_SESION, ENTIDAD, usuario_id=usuario.id, entidad_id=usuario.id)
    db.session.commit()


def cambiar_contrasena(usuario: Usuario, actual: str, nueva: str, confirmacion: str) -> None:
    """RF-03: la contraseña vigente deja de funcionar al guardar la nueva."""
    if not usuario.verificar_contrasena(actual):
        raise ErrorUsuario("La contraseña actual no es correcta.")
    if nueva != confirmacion:
        raise ErrorUsuario("Las contraseñas nuevas no coinciden. Escríbela igual en ambos campos.")
    validar_contrasena(nueva)
    if nueva == actual:
        raise ErrorUsuario("La nueva contraseña debe ser distinta de la actual.")
    usuario.establecer_contrasena(nueva)
    auditoria.registrar(
        auditoria.MODIFICAR,
        ENTIDAD,
        usuario_id=usuario.id,
        entidad_id=usuario.id,
        detalle={"campo": "contraseña"},
    )
    db.session.commit()
