"""Reportes: generar en pantalla (CU-13) y exportar a PDF (CU-14); RF-19 y RF-20."""
from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user

from app.models.usuario import ROL_MICROEMPRENDEDOR
from app.seguridad import rol_requerido
from app.services import reporte as reporte_service
from app.services.formato import hoy_lima
from app.services.periodo import mes_anterior

bp = Blueprint("reportes", __name__, url_prefix="/reportes")

MESES_EN_SELECTOR = 24


@bp.before_request
@rol_requerido(ROL_MICROEMPRENDEDOR)
def _solo_microemprendedores():
    return None


def _meses_disponibles(hoy):
    """Mes actual y los 23 anteriores para el selector del reporte mensual."""
    meses = [hoy.replace(day=1)]
    for _ in range(MESES_EN_SELECTOR - 1):
        meses.append(mes_anterior(meses[-1]))
    return meses


def _pagina(solicitud=None, reporte=None, avisos=(), errores=()):
    hoy = hoy_lima()
    return render_template(
        "reportes/inicio.html",
        hoy=hoy,
        solicitud=solicitud,
        reporte=reporte,
        avisos=avisos,
        errores=errores,
        meses=_meses_disponibles(hoy),
        agrupaciones=reporte_service.AGRUPACIONES,
        mensaje_sin_gastos=reporte_service.MENSAJE_SIN_GASTOS,
    )


@bp.get("")
def inicio():
    """Selector de período y agrupación (por defecto: mes actual por categoría)."""
    solicitud, _, _ = reporte_service.interpretar_solicitud({}, hoy_lima())
    return _pagina(solicitud)


@bp.get("/generar")
def generar():
    solicitud, avisos, errores = reporte_service.interpretar_solicitud(request.args, hoy_lima())
    if errores:
        return _pagina(avisos=avisos, errores=errores)
    reporte = reporte_service.generar(current_user._get_current_object(), solicitud)
    return _pagina(solicitud, reporte, avisos)


@bp.get("/pdf")
def pdf():
    solicitud, _, errores = reporte_service.interpretar_solicitud(request.args, hoy_lima())
    if errores:
        for error in errores:
            flash(error, "error")
        return redirect(url_for("reportes.inicio"))
    reporte = reporte_service.generar(current_user._get_current_object(), solicitud)
    try:
        contenido = reporte_service.generar_pdf(reporte)
    except Exception:  # CU-14, flujo alterno 2a: cualquier falla de ReportLab
        current_app.logger.exception("No se pudo generar el PDF del reporte")
        flash("No se pudo generar el PDF. Vuelve a intentarlo.", "error")
        return redirect(url_for("reportes.generar", **solicitud.como_argumentos()))
    return Response(
        contenido,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{reporte.nombre_archivo}"',
            "Cache-Control": "no-store",
        },
    )
