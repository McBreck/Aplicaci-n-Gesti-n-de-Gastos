"""Administración de cuentas (CU-04). Solo para el rol administrador; no hay rutas de gastos."""
from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user

from app.forms.admin import NuevoUsuarioForm, UsuarioForm
from app.models.usuario import ROL_ADMINISTRADOR
from app.seguridad import rol_requerido
from app.services import usuario as usuario_service
from app.services.usuario import CorreoDuplicado, ErrorUsuario

bp = Blueprint("admin", __name__, url_prefix="/admin")

HTTP_CONFLICTO = 409


@bp.before_request
@rol_requerido(ROL_ADMINISTRADOR)
def _solo_administradores():
    return None


def _cuenta_o_404(id_usuario: int):
    usuario = usuario_service.obtener_cuenta(id_usuario)
    if usuario is None:
        abort(404)
    return usuario


def _actor():
    return current_user._get_current_object()


def _anotar_error(form, error: ErrorUsuario) -> int:
    """Muestra el error bajo su campo y devuelve el código HTTP (409 si el correo ya existe)."""
    nombre_campo = "contrasena_temporal" if error.campo == "contrasena" else error.campo
    campo = getattr(form, nombre_campo or "", None) or form.correo
    campo.errors.append(str(error))
    return HTTP_CONFLICTO if isinstance(error, CorreoDuplicado) else 200


@bp.get("/usuarios")
def listar_usuarios():
    return render_template("admin/usuarios.html", usuarios=usuario_service.listar_cuentas())


@bp.route("/usuarios/nuevo", methods=["GET", "POST"])
def nuevo_usuario():
    form = NuevoUsuarioForm()
    if form.validate_on_submit():
        try:
            usuario = usuario_service.crear_usuario(
                nombre=form.nombre.data,
                correo=form.correo.data,
                nombre_negocio=form.nombre_negocio.data,
                rubro=form.rubro.data,
                contrasena_temporal=form.contrasena_temporal.data,
                actor=_actor(),
            )
        except ErrorUsuario as error:
            estado = _anotar_error(form, error)
            return render_template("admin/usuario_form.html", form=form, nuevo=True), estado
        else:
            flash(f"Cuenta creada para {usuario.nombre}.", "exito")
            return redirect(url_for("admin.listar_usuarios"))
    return render_template("admin/usuario_form.html", form=form, nuevo=True)


@bp.route("/usuarios/<int:id_usuario>/editar", methods=["GET", "POST"])
def editar_usuario(id_usuario: int):
    usuario = _cuenta_o_404(id_usuario)
    form = UsuarioForm(obj=usuario)
    if form.validate_on_submit():
        try:
            usuario_service.editar_usuario(
                usuario,
                nombre=form.nombre.data,
                correo=form.correo.data,
                nombre_negocio=form.nombre_negocio.data,
                rubro=form.rubro.data,
                actor=_actor(),
            )
        except ErrorUsuario as error:
            estado = _anotar_error(form, error)
            return (
                render_template("admin/usuario_form.html", form=form, nuevo=False, usuario=usuario),
                estado,
            )
        else:
            flash("Los datos de la cuenta se guardaron.", "exito")
            return redirect(url_for("admin.listar_usuarios"))
    return render_template("admin/usuario_form.html", form=form, nuevo=False, usuario=usuario)


@bp.post("/usuarios/<int:id_usuario>/estado")
def cambiar_estado(id_usuario: int):
    usuario = _cuenta_o_404(id_usuario)
    activa = usuario_service.cambiar_estado(usuario, _actor())
    estado = "activada" if activa else "desactivada"
    flash(f"La cuenta de {usuario.nombre} fue {estado}.", "exito")
    return redirect(url_for("admin.listar_usuarios"))


@bp.post("/usuarios/<int:id_usuario>/restablecer")
def restablecer_contrasena(id_usuario: int):
    usuario = _cuenta_o_404(id_usuario)
    contrasena = usuario_service.restablecer_contrasena(usuario, _actor())
    # Se muestra una sola vez y no se guarda en la sesión
    return render_template("admin/contrasena_temporal.html", usuario=usuario, contrasena=contrasena)
