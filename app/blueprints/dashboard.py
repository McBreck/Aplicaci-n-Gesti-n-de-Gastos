"""Dashboard del mes (CU-11). En la EDT 3.3 muestra el registro rápido; el resto llega en la EDT 3.6."""
from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

from app.services import categoria as categoria_service
from app.services import gasto as gasto_service
from app.services.formato import hoy_lima

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def inicio():
    # El administrador no ve gastos (RN-13): su inicio es el panel de usuarios
    if current_user.es_administrador:
        return redirect(url_for("admin.listar_usuarios"))
    return render_template(
        "dashboard/inicio.html",
        categorias=categoria_service.listar_categorias(current_user.id),
        metodos=gasto_service.listar_metodos_pago(),
        hoy=hoy_lima(),
    )
