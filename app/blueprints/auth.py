"""Acceso: inicio de sesión (CU-01), cierre (CU-02) y cambio de contraseña (CU-03)."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_user, logout_user

from app.extensions import limiter
from app.forms.auth import CambioContrasenaForm, LoginForm
from app.seguridad import es_destino_seguro, url_inicio
from app.services import auth as auth_service
from app.services.usuario import MENSAJE_POLITICA_CONTRASENA, ErrorUsuario

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_inicio(current_user))

    form = LoginForm()
    error = None
    if form.validate_on_submit():
        resultado = auth_service.autenticar(form.correo.data, form.contrasena.data)
        if resultado.exitoso:
            destino = request.args.get("next")
            # Sesión nueva al autenticarse (evita la fijación de sesión, A07)
            session.clear()
            login_user(resultado.usuario, remember=False)
            session.permanent = True
            if not es_destino_seguro(destino):
                destino = url_inicio(resultado.usuario)
            return redirect(destino)
        error = resultado.error
    return render_template("auth/login.html", form=form, error=error)


@bp.post("/logout")
def logout():
    auth_service.registrar_cierre_sesion(current_user._get_current_object())
    logout_user()
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))


@bp.route("/cuenta/contrasena", methods=["GET", "POST"])
def cuenta():
    form = CambioContrasenaForm()
    error = None
    if form.validate_on_submit():
        try:
            auth_service.cambiar_contrasena(
                current_user._get_current_object(),
                form.contrasena_actual.data,
                form.contrasena_nueva.data,
                form.confirmacion.data,
            )
        except ErrorUsuario as excepcion:
            error = str(excepcion)
        else:
            flash("Tu contraseña se cambió correctamente.", "exito")
            return redirect(url_for("auth.cuenta"))
    return render_template(
        "auth/cuenta.html", form=form, error=error, politica=MENSAJE_POLITICA_CONTRASENA
    )
