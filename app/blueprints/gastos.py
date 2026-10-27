"""Gastos: registrar (CU-05), modificar (CU-06), eliminar (CU-07) y consultar (CU-08)."""
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.forms.gasto import GastoForm
from app.models.usuario import ROL_MICROEMPRENDEDOR
from app.seguridad import es_destino_seguro, rol_requerido
from app.services import categoria as categoria_service
from app.services import gasto as gasto_service
from app.services.formato import hoy_lima, unir_lista

bp = Blueprint("gastos", __name__, url_prefix="/gastos")


@bp.before_request
@rol_requerido(ROL_MICROEMPRENDEDOR)
def _solo_microemprendedores():
    return None


def _usuario():
    return current_user._get_current_object()


def _gasto_o_404(id_gasto: int):
    gasto = gasto_service.obtener_gasto_propio(current_user.id, id_gasto)
    if gasto is None:
        abort(404)
    return gasto


def _destino() -> str:
    """Vuelve a la página de origen (?next=) si es interna; si no, a Mis gastos."""
    destino = request.args.get("next")
    return destino if es_destino_seguro(destino) else url_for("gastos.listar")


def _avisar_guardado(gasto) -> None:
    """RF-06 y flujo alterno 7a: estado de completitud y botón «Completar ahora»."""
    faltantes = gasto.campos_faltantes()
    if not faltantes:
        flash("Gasto guardado · Completo", "exito")
        return
    flash(
        {
            "texto": f"Gasto guardado · Incompleto: falta {unir_lista(faltantes)}",
            "accion_url": url_for("gastos.editar", id_gasto=gasto.id),
            "accion_texto": "Completar ahora",
        },
        "aviso",
    )


def _valores_de(gasto) -> dict:
    return {
        "monto": f"{gasto.monto:.2f}",
        "fecha": gasto.fecha.isoformat(),
        "categoria_id": str(gasto.categoria_id or ""),
        "metodo_pago_id": str(gasto.metodo_pago_id or ""),
        "descripcion": gasto.descripcion or "",
    }


def _formulario(form, valores: dict, errores: dict | None = None, gasto=None):
    categorias = categoria_service.listar_categorias(
        current_user.id, incluir_id=gasto.categoria_id if gasto else None
    )
    return render_template(
        "gastos/formulario.html",
        form=form,
        gasto=gasto,
        valores=valores,
        errores=errores or {},
        faltantes=gasto.campos_faltantes() if gasto else [],
        categorias=categorias,
        metodos=gasto_service.listar_metodos_pago(),
        hoy=hoy_lima(),
        url_volver=_destino(),
    )


@bp.get("")
def listar():
    hoy = hoy_lima()
    filtros, avisos = gasto_service.interpretar_filtros(request.args, hoy)
    resultado = gasto_service.listar_gastos(current_user.id, filtros, request.args.get("pagina", 1, type=int))
    return render_template(
        "gastos/lista.html",
        filtros=filtros,
        avisos=avisos,
        resultado=resultado,
        dias=gasto_service.agrupar_actividad(resultado.gastos, hoy, resultado.totales_por_dia),
        por_defecto=filtros == gasto_service.filtros_por_defecto(hoy),
        categorias=categoria_service.listar_categorias(current_user.id, solo_activas=False),
        metodos=gasto_service.listar_metodos_pago(),
    )


@bp.route("/nuevo", methods=["GET", "POST"])
def nuevo():
    form = GastoForm()
    if form.validate_on_submit():
        try:
            gasto = gasto_service.registrar_gasto(_usuario(), form.datos())
        except gasto_service.ErrorValidacion as error:
            return _formulario(form, form.datos(), error.errores)
        _avisar_guardado(gasto)
        return redirect(_destino())
    # ?categoria= llega desde el "+" de las tarjetas rápidas del inicio (P-02)
    return _formulario(form, {"fecha": hoy_lima().isoformat(), "categoria_id": request.args.get("categoria", "")})


@bp.route("/<int:id_gasto>/editar", methods=["GET", "POST"])
def editar(id_gasto: int):
    gasto = _gasto_o_404(id_gasto)
    form = GastoForm()
    if form.validate_on_submit():
        try:
            gasto_service.modificar_gasto(gasto, _usuario(), form.datos())
        except gasto_service.ErrorValidacion as error:
            return _formulario(form, form.datos(), error.errores, gasto)
        _avisar_guardado(gasto)
        return redirect(_destino())
    return _formulario(form, _valores_de(gasto), gasto=gasto)


@bp.post("/<int:id_gasto>/eliminar")
def eliminar(id_gasto: int):
    gasto = _gasto_o_404(id_gasto)
    gasto_service.eliminar_gasto(gasto, _usuario())
    flash("Gasto eliminado.", "exito")
    return redirect(_destino())
