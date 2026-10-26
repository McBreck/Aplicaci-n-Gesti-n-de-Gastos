"""Configuración común de las pruebas.

La base de TEST_DATABASE_URL (PostgreSQL) se borra y se recrea con la
migración de Alembic al inicio de cada ejecución, así las pruebas validan el
mismo esquema que producción. Después de cada prueba se eliminan los datos
creados y se conservan los catálogos.
"""
from pathlib import Path

import pytest
from dotenv import load_dotenv
from flask import g
from flask.testing import FlaskClient
from flask_migrate import upgrade
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import create_app
from app.extensions import db
from app.models import Usuario

load_dotenv()

CARPETA_MIGRACIONES = str(Path(__file__).resolve().parents[1] / "migrations")

# Orden de borrado respetando las claves foráneas
LIMPIEZA = (
    "DELETE FROM auditoria",
    "DELETE FROM gasto",
    "DELETE FROM presupuesto",
    "DELETE FROM categoria WHERE usuario_id IS NOT NULL",
    "DELETE FROM usuario",
)


class ClientePruebas(FlaskClient):
    """Cada petición empieza con `g` vacío, como en producción.

    Las pruebas mantienen un contexto de aplicación abierto y Flask reutiliza
    su `g` entre peticiones; Flask-Login, CSRF y el limitador guardan ahí datos
    de la petición anterior.
    """

    def open(self, *args, **kwargs):
        g.__dict__.clear()
        return super().open(*args, **kwargs)


def _verificar_base_de_pruebas(url: str) -> None:
    nombre = make_url(url).database or ""
    if "prueba" not in nombre:
        pytest.exit(
            f"TEST_DATABASE_URL apunta a la base '{nombre}', cuyo nombre no contiene 'prueba'. "
            "Se detienen las pruebas para no borrar datos reales.",
            returncode=1,
        )


@pytest.fixture(scope="session")
def app():
    aplicacion = create_app("pruebas")
    aplicacion.test_client_class = ClientePruebas
    _verificar_base_de_pruebas(aplicacion.config["SQLALCHEMY_DATABASE_URI"])
    with aplicacion.app_context():
        with db.engine.begin() as conexion:
            conexion.execute(text("DROP SCHEMA public CASCADE"))
            conexion.execute(text("CREATE SCHEMA public"))
        upgrade(directory=CARPETA_MIGRACIONES)
        yield aplicacion
        db.session.remove()
        db.engine.dispose()


@pytest.fixture
def sesion(app):
    yield db.session
    g.__dict__.clear()
    db.session.rollback()
    for sentencia in LIMPIEZA:
        db.session.execute(text(sentencia))
    db.session.commit()


@pytest.fixture
def cliente(app, sesion):
    return app.test_client()


@pytest.fixture
def ejecutor_cli(app, sesion):
    return app.test_cli_runner()


@pytest.fixture
def crear_usuario(sesion):
    """Crea usuarios PRUEBA con datos mínimos válidos."""

    def _crear(correo: str = "prueba.ana@ejemplo.com", contrasena: str = "clave1234", **campos) -> Usuario:
        usuario = Usuario(nombre=campos.pop("nombre", "PRUEBA Ana"), correo=correo, **campos)
        usuario.establecer_contrasena(contrasena)
        sesion.add(usuario)
        sesion.commit()
        return usuario

    return _crear


@pytest.fixture
def crear_admin(crear_usuario):
    def _crear(correo: str = "prueba.admin@ejemplo.com") -> Usuario:
        return crear_usuario(correo, nombre="PRUEBA Admin", rol="administrador")

    return _crear


@pytest.fixture
def iniciar_sesion(cliente):
    """Inicia sesión con el cliente de pruebas y devuelve la respuesta."""

    def _iniciar(correo: str, contrasena: str = "clave1234", **opciones):
        return cliente.post("/login", data={"correo": correo, "contrasena": contrasena}, **opciones)

    return _iniciar
