"""Presupuesto mensual por categoría (CU-10; RF-12 a RF-14)."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.models.usuario import ROL_MICROEMPRENDEDOR
from app.seguridad import rol_requerido
from app.services import presupuesto as presupuesto_service
from app.services.formato import hoy_lima, mes_anio
from app.services.periodo import interpretar_mes, mes_anterior, mes_siguiente, texto_mes
from app.services.validacion import ErrorValidacion

bp = Blueprint("presupuesto", __name__, url_prefix="/presupuesto")

# Cada monto llega como monto_<id de la categoría>
PREFIJO_MONTO = "monto_"


@bp.before_request
@rol_requerido(ROL_MICROEMPRENDEDOR)
def _solo_microemprendedores():
    return None


def _usuario():
    return current_user._get_current_object()


def _mes_pedido():
    return interpretar_mes(request.args.get("mes"), hoy_lima())


def _montos_del_formulario() -> dict[int, str]:
    montos = {}
    for clave, valor in request.form.items():
        sufijo = clave[len(PREFIJO_MONTO):]
        if clave.startswith(PREFIJO_MONTO) and sufijo.isdigit():
            montos[int(sufijo)] = valor
    return montos


def _vecino(mes):
    """Mes al que lleva una flecha del selector (None si queda fuera del rango editable)."""
    return mes if presupuesto_service.periodo_editable(mes) else None


@bp.route("", methods=["GET", "POST"])
def ver():
    mes = _mes_pedido()
    errores, valores = {}, {}
    if request.method == "POST":
        montos = _montos_del_formulario()
        try:
            cambios = presupuesto_service.guardar_presupuesto(_usuario(), mes, montos)
        except ErrorValidacion as error:
            errores = error.errores
            valores = {str(id_categoria): texto for id_categoria, texto in montos.items()}
        except presupuesto_service.ErrorPresupuesto as error:
            flash(str(error), "aviso")
            return redirect(url_for("presupuesto.ver", mes=texto_mes(mes)))
        else:
            if cambios:
                flash(f"Presupuesto de {mes_anio(mes)} guardado.", "exito")
            else:
                flash("No hubo cambios en el presupuesto.", "info")
            return redirect(url_for("presupuesto.ver", mes=texto_mes(mes)))

    return render_template(
        "presupuesto/mes.html",
        comparacion=presupuesto_service.comparar(current_user.id, mes),
        mes=mes,
        mes_previo=mes_anterior(mes),
        anterior=_vecino(mes_anterior(mes)),
        siguiente=_vecino(mes_siguiente(mes)),
        editable=presupuesto_service.periodo_editable(mes),
        mensaje_periodo=presupuesto_service.MENSAJE_PERIODO,
        errores=errores,
        valores=valores,
    )


@bp.post("/copiar")
def copiar():
    """CU-10, flujo alterno 3a."""
    mes = _mes_pedido()
    try:
        copiados = presupuesto_service.copiar_mes_anterior(_usuario(), mes)
    except presupuesto_service.ErrorPresupuesto as error:
        flash(str(error), "aviso")
    else:
        cantidad = "1 monto" if copiados == 1 else f"{copiados} montos"
        flash(f"Se copiaron {cantidad} de {mes_anio(mes_anterior(mes))}.", "exito")
    return redirect(url_for("presupuesto.ver", mes=texto_mes(mes)))
