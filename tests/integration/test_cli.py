"""Comandos `flask crear-admin`, `flask demo crear` y `flask demo borrar`."""
from datetime import timedelta

import pytest
from sqlalchemy import select

from app import demo
from app.models import Usuario
from app.services.formato import fecha, hoy_lima


def _crear_admin(ejecutor_cli, correo="Admin@Ejemplo.com", contrasena="clave1234"):
    return ejecutor_cli.invoke(
        args=["crear-admin", "--nombre", "PRUEBA Admin", "--correo", correo, "--contrasena", contrasena]
    )


def test_crea_administrador_con_hash_argon2id(ejecutor_cli, sesion):
    resultado = _crear_admin(ejecutor_cli)
    assert resultado.exit_code == 0, resultado.output
    assert "admin@ejemplo.com" in resultado.output

    admin = sesion.scalar(select(Usuario).where(Usuario.correo == "admin@ejemplo.com"))
    assert admin.es_administrador
    assert admin.password_hash.startswith("$argon2id$")
    assert admin.verificar_contrasena("clave1234")


def test_rechaza_contrasena_que_no_cumple_la_politica(ejecutor_cli, sesion):
    for contrasena in ("corta1", "solamenteletras", "1234567890"):
        resultado = _crear_admin(ejecutor_cli, contrasena=contrasena)
        assert resultado.exit_code != 0
        assert "al menos 8 caracteres e incluir letras y números" in resultado.output
    assert sesion.scalar(select(Usuario)) is None


def test_rechaza_correo_duplicado(ejecutor_cli, sesion):
    _crear_admin(ejecutor_cli)
    resultado = _crear_admin(ejecutor_cli, correo="ADMIN@ejemplo.com")
    assert resultado.exit_code != 0
    assert "Ya existe una cuenta con ese correo" in resultado.output


def test_rechaza_correo_invalido(ejecutor_cli, sesion):
    resultado = _crear_admin(ejecutor_cli, correo="sin-arroba")
    assert resultado.exit_code != 0
    assert "correo válido" in resultado.output


# --- flask demo ------------------------------------------------------------------------------------

def _demo_crear(ejecutor_cli, contrasena="Demo2026"):
    return ejecutor_cli.invoke(args=["demo", "crear", "--contrasena", contrasena])


def test_demo_crear_y_borrar(ejecutor_cli, sesion):
    resultado = _demo_crear(ejecutor_cli)
    assert resultado.exit_code == 0, resultado.output
    hoy = hoy_lima()
    assert "Cuenta de demostración creada." in resultado.output
    assert f"Correo: {demo.CORREO}" in resultado.output
    assert f"del {fecha(hoy - timedelta(days=59))} al {fecha(hoy)}" in resultado.output

    repetido = _demo_crear(ejecutor_cli)
    assert repetido.exit_code != 0 and "ya existe" in repetido.output

    cancelado = ejecutor_cli.invoke(args=["demo", "borrar"], input="n\n")
    assert "Se borrará 1 cuenta PRUEBA" in cancelado.output
    assert "PRUEBA Panadería (prueba.panaderia@controlgastos.test)" in cancelado.output
    assert "No se borró nada." in cancelado.output
    assert sesion.scalar(select(Usuario.id).where(Usuario.correo == demo.CORREO)) is not None

    borrado = ejecutor_cli.invoke(args=["demo", "borrar"], input="s\n")
    assert borrado.exit_code == 0, borrado.output
    assert "Datos PRUEBA borrados: 1 cuenta," in borrado.output
    assert sesion.scalar(select(Usuario.id)) is None

    vacio = ejecutor_cli.invoke(args=["demo", "borrar", "--si"])
    assert "No hay datos PRUEBA para borrar." in vacio.output


def test_demo_crear_rechaza_una_contrasena_debil(ejecutor_cli, sesion):
    resultado = _demo_crear(ejecutor_cli, contrasena="corta")
    assert resultado.exit_code != 0
    assert "al menos 8 caracteres e incluir letras y números" in resultado.output
    assert sesion.scalar(select(Usuario.id)) is None


@pytest.mark.parametrize(
    "ruta", ["/", "/api/dashboard", "/gastos", "/presupuesto", "/categorias", "/reportes/generar", "/reportes/pdf"]
)
def test_la_cuenta_de_demostracion_funciona_en_la_app(ejecutor_cli, cliente, iniciar_sesion, ruta):
    _demo_crear(ejecutor_cli)
    iniciar_sesion(demo.CORREO, "Demo2026")
    assert cliente.get(ruta).status_code == 200
