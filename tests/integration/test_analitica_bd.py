"""AnaliticaService con PostgreSQL: construcción del DataFrame, análisis del mes y misma fuente
que el listado (A8) y el presupuesto (A7, A9)."""
from datetime import date
from decimal import Decimal

import pytest

from app.models import Presupuesto
from app.services import analitica
from app.services import gasto as gasto_service
from app.services import presupuesto as presupuesto_service
from app.services.gasto import FiltrosGastos
from tests.datos_verificacion import GASTOS_OCTUBRE_2026, PRESUPUESTO_OCTUBRE_2026

OCTUBRE = date(2026, 10, 1)
FIN_OCTUBRE = date(2026, 10, 31)
HOY = date(2026, 10, 26)


@pytest.fixture
def ana(crear_microemprendedor):
    return crear_microemprendedor()


@pytest.fixture
def octubre(ana, cargar_gastos, sesion, id_categoria):
    gastos = cargar_gastos(ana, GASTOS_OCTUBRE_2026)
    for nombre, monto in PRESUPUESTO_OCTUBRE_2026.items():
        sesion.add(Presupuesto(usuario_id=ana.id, categoria_id=id_categoria(ana, nombre), anio=2026, mes=10,
                               monto=Decimal(monto)))
    sesion.commit()
    return gastos


def test_dataframe_del_usuario_sin_eliminados(ana, octubre, crear_microemprendedor, cargar_gastos):
    luis = crear_microemprendedor("prueba.luis@ejemplo.com")
    cargar_gastos(luis, [("2026-10-03", "999.00", "Alquiler", "Ajeno", "Efectivo")])
    gasto_service.eliminar_gasto(octubre[4], ana)  # 900.00 de alquiler
    df = analitica.construir_dataframe(ana.id, OCTUBRE, FIN_OCTUBRE)
    assert len(df) == 11
    assert analitica.total(df) == Decimal("966.80")
    assert set(df["metodo_pago"]) >= {"Sin registrar", "Efectivo"}
    assert "Sin categoría" in set(df["categoria"])


def test_misma_fuente_que_el_listado_y_el_presupuesto(ana, octubre):
    df = analitica.construir_dataframe(ana.id, OCTUBRE, FIN_OCTUBRE)
    # A8 = completitud de Mis gastos (GastoService)
    assert analitica.completitud(df) == gasto_service.resumir(ana.id, FiltrosGastos(desde=OCTUBRE, hasta=FIN_OCTUBRE))
    # A7 y A9 = comparación de P-05 (PresupuestoService)
    ejecucion = analitica.ejecucion_presupuestaria(df, analitica.presupuestos_del_mes(ana.id, OCTUBRE))
    comparacion = presupuesto_service.comparar(ana.id, OCTUBRE)
    esperado = {f.categoria.nombre: (float(f.ejecutado), f.porcentaje, f.estado) for f in comparacion.con_presupuesto}
    obtenido = {fila.categoria: (fila.ejecutado, fila.porcentaje, fila.estado) for fila in ejecucion.itertuples()}
    assert obtenido == esperado
    assert analitica.presupuesto_usado(ejecucion) == comparacion.porcentaje_usado == 94.5


def test_analisis_del_mes_con_los_datos_de_verificacion(ana, octubre):
    analisis = analitica.analizar_mes(ana.id, OCTUBRE, HOY)
    assert analisis.total == Decimal("1866.80")
    assert analisis.completitud.porcentaje_completitud == 66.7
    assert analisis.completitud.campo_mas_omitido == "método de pago"
    assert analisis.presupuesto_usado == 94.5
    assert analisis.total_planificado == Decimal("1930.00")
    assert (analisis.ejecucion["estado"] != "Excedida").sum() == 4
    assert analisis.variacion is None  # sin gastos en septiembre

    # P1: 9 días con registros y 12 registros; corte en el día 26 (hoy)
    assert analisis.proyeccion.suficiente and analisis.proyeccion.dia_corte == 26
    assert analisis.proyeccion.valor == Decimal("2474.54")

    reglas = [r.regla for r in analisis.recomendaciones]
    assert reglas == ["R2", "R3", "R1"]
    assert analisis.recomendaciones[1].mensaje == (
        "Al ritmo actual cerrarías octubre en S/ 2,474.54, S/ 544.54 por encima de tu presupuesto.")
    assert analisis.recomendaciones[2].mensaje == "Has usado el 100.0 % del presupuesto de Alquiler."


def test_variacion_frente_al_mes_anterior_a_la_misma_fecha(ana, cargar_gastos):
    cargar_gastos(ana, [
        ("2026-09-10", "100.00", "Insumos y materia prima", "Harina", "Efectivo"),
        ("2026-09-28", "500.00", "Insumos y materia prima", "Fuera del corte", "Efectivo"),
        ("2026-10-12", "120.00", "Insumos y materia prima", "Harina", "Efectivo"),
    ])
    analisis = analitica.analizar_mes(ana.id, OCTUBRE, HOY)
    assert analisis.total_anterior == Decimal("100.00")  # solo hasta el 26 de septiembre
    assert analisis.variacion == 20.0
    assert analisis.mensual["total"].tolist()[-2:] == [600.00, 120.00]  # A6


def test_mes_sin_presupuesto_y_presupuesto_en_cero(ana, cargar_gastos, sesion, id_categoria):
    cargar_gastos(ana, [("2026-10-05", "50.00", "Transporte", "Mototaxi", "Efectivo")])
    sin_presupuesto = analitica.analizar_mes(ana.id, OCTUBRE, HOY)
    assert sin_presupuesto.estado_presupuesto is None and sin_presupuesto.porcentaje_barra == 0.0

    for nombre in ("Transporte", "Alquiler"):
        sesion.add(Presupuesto(usuario_id=ana.id, categoria_id=id_categoria(ana, nombre), anio=2026, mes=10,
                               monto=Decimal("0")))
    sesion.commit()
    en_cero = analitica.analizar_mes(ana.id, OCTUBRE, HOY)
    assert en_cero.presupuesto_usado is None  # Σ planificado = 0: sin porcentaje
    assert en_cero.estado_presupuesto == "Excedida"
    assert en_cero.porcentaje_barra == 125.0  # se gastó sin presupuesto: barra llena
    barras = {fila["categoria"]: fila["porcentaje_barra"] for fila in en_cero.mayor_ejecucion()}
    assert barras == {"Transporte": 125.0, "Alquiler": 0.0}


def test_mes_futuro_y_mes_pasado(ana, octubre):
    futuro = analitica.analizar_mes(ana.id, date(2026, 11, 1), HOY)
    assert futuro.sin_gastos and futuro.corte is None
    assert not futuro.proyeccion.suficiente
    assert futuro.recomendaciones == []

    pasado = analitica.analizar_mes(ana.id, OCTUBRE, date(2026, 12, 15))
    assert pasado.corte == FIN_OCTUBRE
    assert pasado.proyeccion.dia_corte == 9  # último día con datos
    assert "R3" not in [r.regla for r in pasado.recomendaciones]  # no se proyecta un mes cerrado
