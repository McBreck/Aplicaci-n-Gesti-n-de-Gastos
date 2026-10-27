"""Categorías: listado, creación, renombrado y activación (CU-09, RF-11)."""
from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user

from app.forms.categoria import CategoriaForm, RenombrarCategoriaForm
from app.models import Categoria
from app.models.categoria import PALETA
from app.models.usuario import ROL_MICROEMPRENDEDOR
from app.seguridad import obtener_propio_o_404, rol_requerido
from app.services import categoria as categoria_service

bp = Blueprint("categorias", __name__, url_prefix="/categorias")


@bp.before_request
@rol_requerido(ROL_MICROEMPRENDEDOR)
def _solo_microemprendedores():
    return None


def _usuario():
    return current_user._get_current_object()


def _pagina(form, errores: dict | None = None, abierta: int | None = None, nombre_propuesto: str | None = None):
    return render_template(
        "categorias/lista.html",
        form=form,
        categorias=categoria_service.listar_categorias(current_user.id, solo_activas=False),
        paleta=PALETA,
        errores=errores or {},
        abierta=abierta,
        nombre_propuesto=nombre_propuesto,
    )


@bp.route("", methods=["GET", "POST"])
def listar():
    form = CategoriaForm()
    if form.validate_on_submit():
        try:
            categoria = categoria_service.crear_categoria(_usuario(), form.nombre.data, form.color.data)
        except categoria_service.ErrorCategoria as error:
            return _pagina(form, errores={"nueva": str(error)})
        flash(f"Categoría «{categoria.nombre}» creada.", "exito")
        return redirect(url_for("categorias.listar"))
    if not form.color.data:
        form.color.data = PALETA[0][0]
    return _pagina(form)


@bp.post("/<int:id_categoria>/editar")
def renombrar(id_categoria: int):
    categoria = obtener_propio_o_404(Categoria, id_categoria)
    form = RenombrarCategoriaForm()
    try:
        categoria_service.renombrar_categoria(categoria, _usuario(), form.nombre.data)
    except categoria_service.ErrorCategoria as error:
        if categoria.predeterminada:
            # La interfaz no ofrece renombrarlas: se avisa sin formulario en línea
            flash(str(error), "error")
            return redirect(url_for("categorias.listar"))
        nueva = CategoriaForm(formdata=None, color=PALETA[0][0])
        return _pagina(
            nueva, errores={categoria.id: str(error)}, abierta=categoria.id, nombre_propuesto=form.nombre.data
        )
    flash("Categoría renombrada.", "exito")
    return redirect(url_for("categorias.listar"))


@bp.post("/<int:id_categoria>/estado")
def cambiar_estado(id_categoria: int):
    categoria = obtener_propio_o_404(Categoria, id_categoria)
    if categoria_service.cambiar_estado(categoria, _usuario()):
        flash(f"Categoría «{categoria.nombre}» activada.", "exito")
    else:
        flash(
            f"Categoría «{categoria.nombre}» desactivada. Ya no aparecerá al registrar gastos; "
            "tus gastos anteriores la conservan.",
            "exito",
        )
    return redirect(url_for("categorias.listar"))
