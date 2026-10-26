"""Dashboard del mes (CU-11). En la EDT 3.2 solo es la página de inicio; se completa en la EDT 3.6."""
from flask import Blueprint, redirect, render_template, url_for
from flask_login import current_user

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def inicio():
    # El administrador no ve gastos (RN-13): su inicio es el panel de usuarios
    if current_user.es_administrador:
        return redirect(url_for("admin.listar_usuarios"))
    return render_template("dashboard/inicio.html")
