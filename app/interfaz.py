"""Elementos comunes de la interfaz: navegación, avatar y páginas de error."""
from flask import Flask, current_app, render_template, request, url_for
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from werkzeug.exceptions import HTTPException

from app.extensions import db
from app.seguridad import url_inicio

# (texto, ícono de Bootstrap Icons, endpoint). Un ítem aparece cuando su ruta existe.
NAVEGACION_MICROEMPRENDEDOR = (
    ("Inicio", "bi-house", "dashboard.inicio"),
    ("Mis gastos", "bi-receipt", "gastos.listar"),
    ("Presupuesto", "bi-pie-chart", "presupuesto.ver"),
    ("Categorías", "bi-tags", "categorias.listar"),
    ("Reportes", "bi-file-earmark-text", "reportes.inicio"),
)
NAVEGACION_ADMINISTRADOR = (
    ("Usuarios", "bi-people", "admin.listar_usuarios"),
    ("Mi cuenta", "bi-person-circle", "auth.cuenta"),
)
ENDPOINT_REGISTRAR_GASTO = "gastos.nuevo"
# En el propio formulario del gasto el FAB sobra y taparía el botón Guardar
ENDPOINTS_SIN_FAB = {"gastos.nuevo", "gastos.editar"}

ERRORES = {
    400: ("Solicitud no válida", "No pudimos procesar lo que enviaste. Revisa los datos y vuelve a intentarlo."),
    403: ("No tienes acceso", "Esta página no está disponible para tu cuenta."),
    404: ("Página no encontrada", "La página que buscas no existe o ya no está disponible."),
    405: ("Acción no permitida", "Esa acción no se puede hacer desde aquí. Vuelve al inicio e inténtalo de nuevo."),
    429: ("Demasiados intentos", "Hiciste muchos intentos seguidos. Espera un minuto y vuelve a intentarlo."),
    500: ("Algo salió mal", "Tuvimos un problema al procesar tu solicitud. Vuelve a intentarlo en unos minutos."),
}
MENSAJE_CSRF = "El formulario expiró por seguridad. Vuelve a cargar la página e inténtalo de nuevo."


def registrar_interfaz(app: Flask) -> None:
    app.context_processor(_contexto_comun)
    app.add_template_filter(iniciales, "iniciales")
    app.register_error_handler(HTTPException, _pagina_error)


def iniciales(nombre: str | None) -> str:
    """'Ana Torres Ruiz' → 'AT'."""
    palabras = (nombre or "").split()
    return "".join(palabra[0] for palabra in palabras[:2]).upper() or "?"


def _construir_navegacion(items) -> list[dict]:
    navegacion = []
    for texto, icono, endpoint in items:
        if endpoint not in current_app.view_functions:
            continue
        blueprint = endpoint.split(".")[0]
        activo = request.endpoint == endpoint or (
            blueprint != "auth" and request.blueprint == blueprint
        )
        navegacion.append(
            {"texto": texto, "icono": icono, "url": url_for(endpoint), "activo": activo, "badge": None}
        )
    return navegacion


def _contexto_comun() -> dict:
    if not current_user.is_authenticated:
        return {}
    es_admin = current_user.es_administrador
    items = NAVEGACION_ADMINISTRADOR if es_admin else NAVEGACION_MICROEMPRENDEDOR
    puede_registrar = (
        not es_admin
        and ENDPOINT_REGISTRAR_GASTO in current_app.view_functions
        and request.endpoint not in ENDPOINTS_SIN_FAB
    )
    return {
        "navegacion": _construir_navegacion(items),
        "url_inicio": url_inicio(current_user),
        "url_registrar_gasto": url_for(ENDPOINT_REGISTRAR_GASTO) if puede_registrar else None,
    }


def _pagina_error(error: HTTPException):
    # Las redirecciones internas de Werkzeug también son HTTPException
    if error.code is None or error.code < 400:
        return error
    codigo = error.code
    titulo, mensaje = ERRORES.get(codigo, ERRORES[500] if codigo >= 500 else ERRORES[400])
    if isinstance(error, CSRFError):
        mensaje = MENSAJE_CSRF
    if codigo >= 500:
        db.session.rollback()
    return render_template("errores/error.html", codigo=codigo, titulo=titulo, mensaje=mensaje), codigo
