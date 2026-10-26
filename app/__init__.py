"""Fábrica de la aplicación ControlGastos."""
import os

from flask import Flask, jsonify
from flask_talisman import Talisman
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import CONFIGURACIONES
from app.extensions import csrf, db, limiter, login_manager, migrate
from app.services import formato

# Política de seguridad de contenido: todo se sirve desde el propio dominio (A05).
# img-src admite data: porque Bootstrap dibuja algunos controles de formulario
# con imágenes SVG incrustadas en su CSS.
POLITICA_CSP = {
    "default-src": "'self'",
    "img-src": ["'self'", "data:"],
}

LONGITUD_MINIMA_SECRET_KEY = 32
PREFIJO_POSTGRESQL = "postgresql"
PREFIJO_PSYCOPG = "postgresql+psycopg://"


class ErrorConfiguracion(RuntimeError):
    """La configuración del entorno impide arrancar la aplicación."""


def create_app(entorno: str | None = None, **config_extra) -> Flask:
    """Crea la aplicación para el entorno indicado o el de APP_ENV."""
    entorno = (entorno or os.environ.get("APP_ENV", "desarrollo")).strip().lower()
    if entorno not in CONFIGURACIONES:
        raise ErrorConfiguracion(
            f"APP_ENV='{entorno}' no es válido. Usa: desarrollo, pruebas o produccion."
        )

    app = Flask(__name__)
    app.config.from_object(CONFIGURACIONES[entorno]())
    app.config["APP_ENV"] = entorno
    app.config.update(config_extra)
    _validar_configuracion(app)

    _registrar_extensiones(app)
    talisman = _registrar_seguridad(app)
    _registrar_filtros(app)
    _registrar_rutas_base(app, talisman)
    _registrar_blueprints(app)
    _registrar_comandos(app)
    return app


def normalizar_url_bd(url: str) -> str:
    """Usa siempre el controlador psycopg 3 para las URL postgresql://."""
    if url.startswith("postgresql://"):
        return PREFIJO_PSYCOPG + url[len("postgresql://"):]
    return url


def _validar_configuracion(app: Flask) -> None:
    entorno = app.config["APP_ENV"]
    variable = "TEST_DATABASE_URL" if entorno == "pruebas" else "DATABASE_URL"
    url = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
    if not url.startswith(PREFIJO_POSTGRESQL):
        # Solo se muestra el tipo de base, nunca la URL (puede contener la contraseña)
        tipo = url.split(":", 1)[0] if url else "vacía"
        raise ErrorConfiguracion(
            f"ControlGastos solo funciona con PostgreSQL 16. La variable {variable} "
            f"debe empezar con '{PREFIJO_PSYCOPG}' (se recibió: {tipo}). "
            "Revisa tu archivo .env."
        )
    app.config["SQLALCHEMY_DATABASE_URI"] = normalizar_url_bd(url)

    clave = app.config.get("SECRET_KEY") or ""
    if not clave:
        raise ErrorConfiguracion(
            "Falta SECRET_KEY en el archivo .env. Genera una con: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )
    if entorno == "produccion" and len(clave) < LONGITUD_MINIMA_SECRET_KEY:
        raise ErrorConfiguracion(
            f"En producción, SECRET_KEY debe tener al menos {LONGITUD_MINIMA_SECRET_KEY} caracteres."
        )


def _registrar_extensiones(app: Flask) -> None:
    from app import models  # noqa: F401  (registra los modelos en SQLAlchemy)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)

    login_manager.init_app(app)
    login_manager.session_protection = "strong"
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."
    login_manager.login_message_category = "info"


def _registrar_seguridad(app: Flask) -> Talisman:
    from app.seguridad import exigir_sesion

    app.before_request(exigir_sesion)
    forzar_https = app.config["FORZAR_HTTPS"]
    if app.config["APP_ENV"] == "produccion":
        # Nginx entrega la IP real del cliente y el esquema original (A05, A09)
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)
    return Talisman(
        app,
        force_https=forzar_https,
        strict_transport_security=forzar_https,
        session_cookie_secure=app.config["SESSION_COOKIE_SECURE"],
        content_security_policy=POLITICA_CSP,
    )


def _registrar_filtros(app: Flask) -> None:
    app.add_template_filter(formato.soles, "soles")
    app.add_template_filter(formato.fecha, "fecha")
    app.add_template_filter(formato.fecha_hora, "fecha_hora")
    app.add_template_filter(formato.fecha_corta, "fecha_corta")
    app.add_template_filter(formato.mes_anio, "mes_anio")
    app.add_template_filter(formato.color_texto, "color_texto")


def _registrar_rutas_base(app: Flask, talisman: Talisman) -> None:
    @app.get("/salud")
    @talisman(force_https=False)
    def salud():
        """Monitoreo de disponibilidad (RNF-13): no expone datos."""
        return jsonify(estado="ok")


def _registrar_blueprints(app: Flask) -> None:
    from app.blueprints import registrar_blueprints
    from app.interfaz import registrar_interfaz

    registrar_blueprints(app)
    registrar_interfaz(app)


def _registrar_comandos(app: Flask) -> None:
    from app.cli import registrar_comandos

    registrar_comandos(app)
