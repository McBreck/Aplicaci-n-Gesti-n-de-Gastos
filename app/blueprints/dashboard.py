"""Dashboard del mes (CU-11, CU-12; RF-13 a RF-18): página P-02 y datos de los gráficos."""
from datetime import date, timedelta

from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.interfaz import resumen_del_mes_actual
from app.models.usuario import ROL_MICROEMPRENDEDOR
from app.seguridad import rol_requerido
from app.services import analitica
from app.services import categoria as categoria_service
from app.services import gasto as gasto_service
from app.services.formato import hoy_lima
from app.services.gasto import FiltrosGastos
from app.services.periodo import ANIO_MINIMO_LECTURA, interpretar_mes, mes_anterior, mes_siguiente, ultimo_dia
from app.services.recomendacion import MENSAJE_BAJO_CONTROL

bp = Blueprint("dashboard", __name__)

DIAS_ACTIVIDAD = 7


def _mes_pedido(hoy: date) -> date:
    """Mes de ?mes=AAAA-MM; nunca uno futuro."""
    return min(interpretar_mes(request.args.get("mes"), hoy), hoy.replace(day=1))


def _semana_pedida(analisis, hoy: date) -> date:
    """Lunes de ?semana=AAAA-MM-DD; por defecto, la semana del día de corte del mes."""
    referencia = analisis.corte or ultimo_dia(analisis.mes)
    texto = request.args.get("semana", "")
    try:
        referencia = date.fromisoformat(texto)
    except ValueError:
        pass
    return analitica.inicio_de_semana(min(referencia, hoy))


@bp.get("/")
def inicio():
    # El administrador no ve gastos (RN-13): su inicio es el panel de usuarios
    if current_user.es_administrador:
        return redirect(url_for("admin.listar_usuarios"))
    hoy = hoy_lima()
    mes = _mes_pedido(hoy)
    analisis = analitica.analizar_mes(current_user.id, mes, hoy)

    referencia = analisis.corte or ultimo_dia(mes)
    filtros = FiltrosGastos(desde=referencia - timedelta(days=DIAS_ACTIVIDAD - 1), hasta=referencia)
    recientes = gasto_service.listar_gastos(current_user.id, filtros)
    montos_del_mes = {fila.categoria.id: fila.ejecutado for fila in resumen_del_mes_actual().filas}
    anterior = mes_anterior(mes)
    siguiente = mes_siguiente(mes)

    return render_template(
        "dashboard/inicio.html",
        mes=mes,
        mes_previo=anterior,
        hoy=hoy,
        analisis=analisis,
        anterior=anterior if anterior.year >= ANIO_MINIMO_LECTURA else None,
        siguiente=siguiente if siguiente <= hoy.replace(day=1) else None,
        categorias=categoria_service.listar_categorias(current_user.id),
        metodos=gasto_service.listar_metodos_pago(),
        rapidas=categoria_service.mas_usadas(current_user.id, hoy),
        montos_del_mes=montos_del_mes,
        dias_actividad=gasto_service.agrupar_actividad(
            recientes.gastos, hoy, recientes.totales_por_dia, agrupar_categorias=True
        ),
        filtros_actividad=filtros,
        mensaje_bajo_control=MENSAJE_BAJO_CONTROL,
    )


@bp.get("/api/dashboard")
@rol_requerido(ROL_MICROEMPRENDEDOR)
def api():
    """JSON para Chart.js (?mes=AAAA-MM&semana=AAAA-MM-DD). Solo datos del usuario autenticado."""
    hoy = hoy_lima()
    analisis = analitica.analizar_mes(current_user.id, _mes_pedido(hoy), hoy)
    lunes = _semana_pedida(analisis, hoy)
    semana = analitica.semana_apilada(
        analitica.construir_dataframe(current_user.id, lunes, lunes + timedelta(days=6)), lunes
    )
    return jsonify(analitica.datos_graficos(analisis, semana, hoy))
