"""La aplicación solo arranca con PostgreSQL y con una configuración válida (sección 3)."""
from datetime import timedelta

import pytest

from app import ErrorConfiguracion, create_app, normalizar_url_bd

URL_POSTGRESQL = "postgresql+psycopg://usuario:clave@localhost:5432/controlgastos"


@pytest.fixture
def entorno_limpio(monkeypatch):
    for variable in ("APP_ENV", "DATABASE_URL", "TEST_DATABASE_URL", "SECRET_KEY"):
        monkeypatch.delenv(variable, raising=False)
    return monkeypatch


@pytest.mark.parametrize(
    "url",
    ["sqlite:///controlgastos.db", "sqlite://", "mysql://root:secreto@localhost/cg", "postgres://u:p@h/db"],
)
def test_se_niega_a_arrancar_sin_postgresql(entorno_limpio, url):
    entorno_limpio.setenv("DATABASE_URL", url)
    entorno_limpio.setenv("SECRET_KEY", "x" * 64)
    with pytest.raises(ErrorConfiguracion, match="solo funciona con PostgreSQL") as error:
        create_app("desarrollo")
    assert "secreto" not in str(error.value)


def test_se_niega_a_arrancar_sin_url(entorno_limpio):
    entorno_limpio.setenv("SECRET_KEY", "x" * 64)
    with pytest.raises(ErrorConfiguracion, match="DATABASE_URL"):
        create_app("desarrollo")


def test_pruebas_exigen_postgresql_en_test_database_url(entorno_limpio):
    entorno_limpio.setenv("TEST_DATABASE_URL", "sqlite:///:memory:")
    with pytest.raises(ErrorConfiguracion, match="TEST_DATABASE_URL"):
        create_app("pruebas")


def test_entorno_desconocido(entorno_limpio):
    with pytest.raises(ErrorConfiguracion, match="APP_ENV"):
        create_app("staging")


def test_exige_secret_key(entorno_limpio):
    entorno_limpio.setenv("DATABASE_URL", URL_POSTGRESQL)
    with pytest.raises(ErrorConfiguracion, match="SECRET_KEY"):
        create_app("desarrollo")


def test_produccion_exige_secret_key_larga(entorno_limpio):
    entorno_limpio.setenv("DATABASE_URL", URL_POSTGRESQL)
    entorno_limpio.setenv("SECRET_KEY", "corta")
    with pytest.raises(ErrorConfiguracion, match="al menos 32"):
        create_app("produccion")


def test_normaliza_url_al_controlador_psycopg():
    assert normalizar_url_bd("postgresql://u:p@h/db") == "postgresql+psycopg://u:p@h/db"
    assert normalizar_url_bd(URL_POSTGRESQL) == URL_POSTGRESQL


def test_configuracion_de_sesion_y_cookies(app):
    assert app.config["PERMANENT_SESSION_LIFETIME"] == timedelta(minutes=30)
    assert app.config["SESSION_REFRESH_EACH_REQUEST"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    assert app.config["ZONA_HORARIA"] == "America/Lima"
    assert app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql+psycopg://")
