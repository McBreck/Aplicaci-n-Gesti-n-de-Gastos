"""Comando `flask crear-admin`."""
from sqlalchemy import select

from app.models import Usuario


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
