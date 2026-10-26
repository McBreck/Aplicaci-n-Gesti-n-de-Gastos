"""Configuración por entorno, elegida con la variable APP_ENV.

Los valores que dependen del archivo .env se leen como propiedades al crear
la aplicación (no al importar este módulo), para que cada create_app() vea
el entorno vigente.
"""
import os
from datetime import timedelta


class Config:
    """Valores comunes a todos los entornos."""

    ZONA_HORARIA = "America/Lima"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Sesión de 30 minutos que se renueva con cada petición (RF-02, OWASP A07)
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_REFRESH_EACH_REQUEST = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False

    # Límite de peticiones en memoria de cada proceso (OWASP A04)
    RATELIMIT_STORAGE_URI = "memory://"

    # HTTPS obligatorio y HSTS (solo en producción, OWASP A05)
    FORZAR_HTTPS = False

    @property
    def SECRET_KEY(self) -> str:
        return os.environ.get("SECRET_KEY", "")

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return os.environ.get("DATABASE_URL", "")


class Desarrollo(Config):
    DEBUG = True


class Pruebas(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False

    @property
    def SECRET_KEY(self) -> str:
        return os.environ.get("SECRET_KEY") or "clave-solo-para-pruebas-automatizadas"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return os.environ.get("TEST_DATABASE_URL", "")


class Produccion(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    PREFERRED_URL_SCHEME = "https"
    FORZAR_HTTPS = True


CONFIGURACIONES = {
    "desarrollo": Desarrollo,
    "pruebas": Pruebas,
    "produccion": Produccion,
}
