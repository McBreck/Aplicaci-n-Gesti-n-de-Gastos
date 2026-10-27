"""AuthService (RF-01 a RF-03, RNF-11): autenticación, bloqueo, bitácora y cambio de contraseña."""
from datetime import timedelta

import pytest
from argon2 import PasswordHasher
from sqlalchemy import select

from app.models import Auditoria
from app.services import auth as auth_service
from app.services.formato import ahora_lima
from app.services.usuario import ErrorUsuario

CORREO = "prueba.ana@ejemplo.com"


def _motivos(sesion) -> list[str]:
    eventos = sesion.scalars(select(Auditoria).where(Auditoria.accion == "LOGIN_FALLIDO").order_by(Auditoria.id))
    return [evento.detalle["motivo"] for evento in eventos]


def test_ingreso_correcto_reinicia_el_contador_y_registra_el_acceso(sesion, crear_usuario):
    ana = crear_usuario(intentos_fallidos=3)
    resultado = auth_service.autenticar(" Prueba.Ana@Ejemplo.com ", "clave1234")
    assert resultado.exitoso and resultado.usuario.id == ana.id
    assert (ana.intentos_fallidos, ana.bloqueado_hasta) == (0, None)
    assert ana.ultimo_acceso is not None
    evento = sesion.scalar(select(Auditoria))
    assert (evento.accion, evento.usuario_id) == ("INICIO_SESION", ana.id)


def test_motivo_de_cada_intento_fallido(sesion, crear_usuario):
    ana = crear_usuario()
    assert auth_service.autenticar("prueba.nadie@ejemplo.com", "x").error == auth_service.MENSAJE_CREDENCIALES
    assert auth_service.autenticar(CORREO, "incorrecta1").error == auth_service.MENSAJE_CREDENCIALES
    ana.activo = False
    sesion.commit()
    assert auth_service.autenticar(CORREO, "clave1234").error == auth_service.MENSAJE_DESACTIVADA
    assert _motivos(sesion) == ["correo_no_registrado", "contrasena_incorrecta", "cuenta_desactivada"]
    sin_cuenta = sesion.scalar(select(Auditoria).where(Auditoria.usuario_id.is_(None)))
    assert sin_cuenta.detalle["correo"] == "prueba.nadie@ejemplo.com"


def test_bloqueo_de_15_minutos_tras_cinco_intentos(sesion, crear_usuario):
    ana = crear_usuario()
    for _ in range(4):
        auth_service.autenticar(CORREO, "incorrecta1")
    resultado = auth_service.autenticar(CORREO, "incorrecta1")
    assert resultado.error.startswith("Por seguridad, tu cuenta está bloqueada")
    assert auth_service.esta_bloqueado(ana) and ana.intentos_fallidos == 0
    # Mientras dura el bloqueo, ni la contraseña correcta permite ingresar (RNF-11)
    assert auth_service.autenticar(CORREO, "clave1234").exitoso is False
    assert _motivos(sesion)[-2:] == ["bloqueo_por_intentos", "cuenta_bloqueada"]

    ana.bloqueado_hasta = ahora_lima() - timedelta(seconds=1)
    sesion.commit()
    assert auth_service.autenticar(CORREO, "clave1234").exitoso


def test_actualiza_el_hash_creado_con_parametros_antiguos(sesion, crear_usuario):
    ana = crear_usuario()
    ana.password_hash = PasswordHasher(time_cost=1, memory_cost=8192).hash("clave1234")
    sesion.commit()
    assert ana.necesita_rehash()
    assert auth_service.autenticar(CORREO, "clave1234").exitoso
    assert not ana.necesita_rehash() and ana.verificar_contrasena("clave1234")


def test_cierre_de_sesion_en_la_bitacora(sesion, crear_usuario):
    ana = crear_usuario()
    auth_service.registrar_cierre_sesion(ana)
    evento = sesion.scalar(select(Auditoria))
    assert (evento.accion, evento.usuario_id, evento.entidad_id) == ("CIERRE_SESION", ana.id, ana.id)


@pytest.mark.parametrize(
    ("actual", "nueva", "confirmacion", "mensaje"),
    [
        ("otra1234", "nueva1234", "nueva1234", "La contraseña actual no es correcta"),
        ("clave1234", "nueva1234", "nueva12345", "no coinciden"),
        ("clave1234", "corta1", "corta1", "al menos 8 caracteres"),
        ("clave1234", "clave1234", "clave1234", "distinta de la actual"),
    ],
)
def test_cambio_de_contrasena_rechazado(sesion, crear_usuario, actual, nueva, confirmacion, mensaje):
    ana = crear_usuario()
    with pytest.raises(ErrorUsuario, match=mensaje):
        auth_service.cambiar_contrasena(ana, actual, nueva, confirmacion)
    assert ana.verificar_contrasena("clave1234")
    assert sesion.scalar(select(Auditoria)) is None


def test_cambio_de_contrasena(sesion, crear_usuario):
    ana = crear_usuario()
    auth_service.cambiar_contrasena(ana, "clave1234", "nueva1234", "nueva1234")
    assert ana.verificar_contrasena("nueva1234") and not ana.verificar_contrasena("clave1234")
    evento = sesion.scalar(select(Auditoria))
    assert (evento.accion, evento.detalle) == ("MODIFICAR", {"campo": "contraseña"})  # nunca la contraseña
