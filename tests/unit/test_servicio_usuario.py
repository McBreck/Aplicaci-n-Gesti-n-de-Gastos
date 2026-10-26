"""UsuarioService y AuthService: reglas que no dependen de las rutas."""
from datetime import timedelta

import pytest

from app.services import auth as auth_service
from app.services import usuario as usuario_service
from app.services.formato import ahora_lima


def test_contrasena_temporal_cumple_la_politica():
    for _ in range(50):
        temporal = usuario_service.generar_contrasena_temporal()
        assert len(temporal) == 10
        usuario_service.validar_contrasena(temporal)
        assert not set(temporal) & set("0O1lI")


@pytest.mark.parametrize("contrasena", ["", None, "abc123", "abcdefgh", "12345678"])
def test_politica_rechaza(contrasena):
    with pytest.raises(usuario_service.ErrorUsuario) as error:
        usuario_service.validar_contrasena(contrasena)
    assert error.value.campo == "contrasena"


@pytest.mark.parametrize("contrasena", ["clave123", "Contraseña1", "12345abc"])
def test_politica_acepta(contrasena):
    usuario_service.validar_contrasena(contrasena)


def test_mensaje_de_bloqueo_en_singular_y_plural():
    assert auth_service.mensaje_bloqueo(ahora_lima() + timedelta(seconds=30)).endswith("en 1 minuto.")
    assert auth_service.mensaje_bloqueo(ahora_lima() + timedelta(minutes=15)).endswith("en 15 minutos.")


def test_resultado_de_autenticacion():
    assert auth_service.ResultadoAutenticacion(error="x").exitoso is False


def test_crear_usuario_copia_solo_plantilla_activa(app, sesion, crear_admin):
    from sqlalchemy import select

    from app.models import Categoria

    admin = crear_admin()
    otros = sesion.scalar(select(Categoria).where(Categoria.usuario_id.is_(None), Categoria.nombre == "Otros"))
    otros.activa = False
    sesion.commit()
    try:
        cuenta = usuario_service.crear_usuario(
            nombre="PRUEBA Rosa", correo="prueba.rosa@ejemplo.com", nombre_negocio="", rubro=None,
            contrasena_temporal="temporal123", actor=admin,
        )
        nombres = sesion.scalars(select(Categoria.nombre).where(Categoria.usuario_id == cuenta.id)).all()
        assert len(nombres) == 8
        assert "Otros" not in nombres
        assert cuenta.nombre_negocio is None
    finally:
        otros.activa = True
        sesion.commit()


def test_editar_sin_cambios_no_registra_auditoria(app, sesion, crear_admin, crear_usuario):
    from sqlalchemy import func, select

    from app.models import Auditoria

    admin = crear_admin()
    cuenta = crear_usuario()
    usuario_service.editar_usuario(
        cuenta, nombre=cuenta.nombre, correo=cuenta.correo, nombre_negocio=None, rubro=None, actor=admin
    )
    assert sesion.scalar(select(func.count()).select_from(Auditoria)) == 0
