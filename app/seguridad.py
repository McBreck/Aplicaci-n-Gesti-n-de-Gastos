"""Control de acceso (OWASP A01): sesión obligatoria, roles y datos propios."""
from functools import wraps
from urllib.parse import urlsplit

from flask import abort, request, url_for
from flask_login import current_user
from sqlalchemy import select

from app.extensions import db, login_manager

# Únicas rutas accesibles sin iniciar sesión
ENDPOINTS_PUBLICOS = {"auth.login", "salud", "static"}


def exigir_sesion():
    """before_request global: todas las rutas exigen sesión salvo las públicas."""
    if request.endpoint is None or request.endpoint in ENDPOINTS_PUBLICOS:
        return None
    if not current_user.is_authenticated:
        return login_manager.unauthorized()
    return None


def rol_requerido(rol: str):
    """Responde 403 si la persona autenticada no tiene el rol indicado."""

    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.rol != rol:
                abort(403)
            return vista(*args, **kwargs)

        return envoltura

    return decorador


def obtener_propio_o_404(modelo, id_registro: int):
    """Registro del usuario autenticado; un id ajeno o inexistente responde 404 (RNF-09)."""
    consulta = select(modelo).where(modelo.id == id_registro, modelo.usuario_id == current_user.id)
    registro = db.session.scalar(consulta)
    if registro is None:
        abort(404)
    return registro


def url_inicio(usuario) -> str:
    """Dashboard para el microemprendedor; panel de usuarios para el administrador (RF-01)."""
    if usuario.es_administrador:
        return url_for("admin.listar_usuarios")
    return url_for("dashboard.inicio")


def es_destino_seguro(destino: str | None) -> bool:
    """Solo rutas internas para ?next= (evita redirecciones a otros sitios)."""
    if not destino or not destino.startswith("/") or destino.startswith(("//", "/\\")):
        return False
    partes = urlsplit(destino)
    return not partes.scheme and not partes.netloc
