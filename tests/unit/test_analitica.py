"""AnaliticaService: métricas A1–A9 y S1 como funciones puras, con los datos de verificación (sección 9)."""
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from app.services import analitica
from tests.datos_verificacion import GASTOS_OCTUBRE_2026, PRESUPUESTO_OCTUBRE_2026

OCTUBRE = date(2026, 10, 1)
FIN_OCTUBRE = date(2026, 10, 31)

# Ids y colores ficticios en el orden de la plantilla (RN-11)
CATEGORIAS = {
    "Insumos y materia prima": (1, "#8B7BFF"),
    "Mercadería": (2, "#FFD166"),
    "Servicios (luz, agua, gas)": (3, "#7EF0C0"),
    "Alquiler": (4, "#93C5FD"),
    "Transporte": (5, "#F9A8D4"),
    "Empaques y envases": (8, "#67E8F9"),
}
METODOS = {"Efectivo": 1, "Yape": 2, "Plin": 3, "Transferencia bancaria": 4, "Tarjeta": 5}


def dataframe_de(gastos) -> pd.DataFrame:
    filas = []
    for indice, (fecha, monto, categoria, descripcion, metodo) in enumerate(gastos, 1):
        id_categoria, color = CATEGORIAS[categoria] if categoria else (None, None)
        filas.append((indice, date.fromisoformat(fecha), Decimal(monto), id_categoria, categoria, color,
                      METODOS.get(metodo), metodo, descripcion))
    return analitica.normalizar(filas)


def presupuestos_de(montos: dict) -> pd.DataFrame:
    filas = [(CATEGORIAS[nombre][0], nombre, CATEGORIAS[nombre][1], float(monto)) for nombre, monto in montos.items()]
    return pd.DataFrame(filas, columns=["categoria_id", "categoria", "color", "planificado"])


@pytest.fixture
def df():
    return dataframe_de(GASTOS_OCTUBRE_2026)


@pytest.fixture
def vacio():
    return analitica.normalizar([])


# --- Construcción ----------------------------------------------------------------------------

def test_vacios_se_rellenan(df):
    assert (df["categoria"] == "Sin categoría").sum() == 1
    assert (df["metodo_pago"] == "Sin registrar").sum() == 2
    assert df.loc[df["categoria"] == "Sin categoría", "color"].iloc[0] == analitica.COLOR_SIN_CATEGORIA


# --- A1 y A2 ---------------------------------------------------------------------------------------

def test_a1_total_del_periodo(df, vacio):
    assert analitica.total(df) == Decimal("1866.80")
    assert analitica.total(vacio) == Decimal("0.00")


@pytest.mark.parametrize(
    ("actual", "anterior", "esperado"),
    [("120", "100", 20.0), ("80", "100", -20.0), ("1866.80", "1660.50", 12.4), ("50", "0", None)],
)
def test_a2_variacion(actual, anterior, esperado):
    assert analitica.variacion_porcentual(Decimal(actual), Decimal(anterior)) == esperado


# --- A3 y A4 -----------------------------------------------------------------------------------------

def test_a3_por_categoria_suma_el_total(df):
    tabla = analitica.por_categoria(df)
    assert round(tabla["total"].sum(), 2) == 1866.80  # RF-16
    assert tabla.iloc[0]["categoria"] == "Alquiler"
    filas = {fila.categoria: (fila.cantidad, fila.total, fila.porcentaje) for fila in tabla.itertuples()}
    assert filas["Servicios (luz, agua, gas)"] == (3, 550.30, 29.5)
    assert filas["Insumos y materia prima"] == (4, 318.50, 17.1)
    assert filas["Sin categoría"] == (1, 42.00, 2.2)
    assert round(sum(filas[nombre][2] for nombre in filas), 1) == 100.0


def test_a4_por_metodo_con_sin_registrar(df):
    tabla = analitica.por_metodo(df)
    totales = dict(zip(tabla["metodo_pago"], tabla["total"]))
    assert totales == {"Transferencia bancaria": 1112.30, "Sin registrar": 338.00, "Efectivo": 262.00,
                       "Yape": 136.50, "Plin": 18.00}
    assert round(sum(totales.values()), 2) == 1866.80


# --- A5 y A6 ---------------------------------------------------------------------------------------------

def test_a5_evolucion_diaria_y_acumulada(df):
    diaria = analitica.evolucion_diaria(df, OCTUBRE, FIN_OCTUBRE)
    assert len(diaria) == 31
    assert diaria["total"].iloc[0] == 214.00  # dos gastos el 1 de octubre
    assert diaria["acumulado"].iloc[8] == 1866.80  # día 9
    assert (diaria["total"].iloc[9:] == 0).all()  # relleno en cero
    assert diaria["acumulado"].iloc[-1] == 1866.80


def test_a6_evolucion_de_seis_meses(df, vacio):
    mensual = analitica.evolucion_mensual(df, OCTUBRE)
    assert [mes.month for mes in mensual["mes"]] == [5, 6, 7, 8, 9, 10]
    assert mensual["total"].tolist() == [0, 0, 0, 0, 0, 1866.80]
    assert analitica.evolucion_mensual(vacio, OCTUBRE)["total"].sum() == 0


# --- A7, A8 y A9 (Ficha de registro N.° 1) --------------------------------------------------------------

def test_a7_ejecucion_presupuestaria(df):
    ejecucion = analitica.ejecucion_presupuestaria(df, presupuestos_de(PRESUPUESTO_OCTUBRE_2026))
    filas = {fila.categoria: (fila.ejecutado, fila.porcentaje, fila.estado) for fila in ejecucion.itertuples()}
    assert filas == {
        "Insumos y materia prima": (318.50, 79.6, "Controlada"),
        "Servicios (luz, agua, gas)": (550.30, 105.8, "Excedida"),
        "Empaques y envases": (50.00, 83.3, "En alerta"),
        "Alquiler": (900.00, 100.0, "En alerta"),
        "Transporte": (6.00, 12.0, "Controlada"),
    }
    assert (ejecucion["estado"] != "Excedida").sum() == 4  # 4 de 5 categorías controladas


@pytest.mark.parametrize(
    ("monto", "estado"),
    [("79.90", "Controlada"), ("80.00", "En alerta"), ("100.00", "En alerta"), ("100.10", "Excedida")],
)
def test_a7_limites_de_estado(monto, estado):
    df = dataframe_de([("2026-10-01", monto, "Alquiler", "x", "Efectivo")])
    ejecucion = analitica.ejecucion_presupuestaria(df, presupuestos_de({"Alquiler": "100.00"}))
    assert ejecucion["estado"].iloc[0] == estado


def test_a8_completitud(df, vacio):
    resumen = analitica.completitud(df)
    assert (resumen.porcentaje_completitud, resumen.completos, resumen.cantidad) == (66.7, 8, 12)
    assert resumen.campo_mas_omitido == "método de pago"
    assert resumen.faltantes == {"categoría": 1, "descripción": 1, "método de pago": 2}
    assert analitica.completitud(vacio).porcentaje_completitud is None


def test_a9_presupuesto_usado(df):
    ejecucion = analitica.ejecucion_presupuestaria(df, presupuestos_de(PRESUPUESTO_OCTUBRE_2026))
    assert analitica.presupuesto_usado(ejecucion) == 94.5  # 1,824.80 / 1,930.00
    sin_presupuesto = analitica.ejecucion_presupuestaria(df, presupuestos_de({}))
    assert analitica.presupuesto_usado(sin_presupuesto) is None


# --- S1 ----------------------------------------------------------------------------------------------------

def test_s1_semana_apilada(df):
    lunes = analitica.inicio_de_semana(date(2026, 10, 8))
    assert lunes == date(2026, 10, 5)
    semana = analitica.semana_apilada(df, lunes)
    assert semana.etiquetas == ("lun 5", "mar 6", "mié 7", "jue 8", "vie 9", "sáb 10", "dom 11")
    assert semana.total == 679.80
    series = {serie["categoria"]: serie for serie in semana.series}
    assert [serie["categoria"] for serie in semana.series][0] == "Servicios (luz, agua, gas)"
    assert series["Servicios (luz, agua, gas)"]["valores"] == [0, 212.30, 0, 0, 280.00, 0, 0]
    assert series["Insumos y materia prima"]["total"] == 104.50
    assert series["Sin categoría"]["categoria_id"] is None
    assert round(sum(serie["total"] for serie in semana.series), 2) == semana.total


def test_s1_semana_sin_gastos(vacio):
    semana = analitica.semana_apilada(vacio, date(2026, 10, 5))
    assert (semana.series, semana.total) == ((), 0.0)


# --- Corte y mes anterior a la misma fecha -------------------------------------------------------------------

def test_corte_del_mes():
    hoy = date(2026, 10, 26)
    assert analitica.corte_del_mes(OCTUBRE, hoy) == hoy
    assert analitica.corte_del_mes(date(2026, 9, 1), hoy) == date(2026, 9, 30)
    assert analitica.corte_del_mes(date(2026, 11, 1), hoy) is None


@pytest.mark.parametrize(
    ("mes", "corte", "esperado"),
    [
        (OCTUBRE, date(2026, 10, 26), (date(2026, 9, 1), date(2026, 9, 26))),
        (date(2026, 3, 1), date(2026, 3, 30), (date(2026, 2, 1), date(2026, 2, 28))),
        (OCTUBRE, FIN_OCTUBRE, (date(2026, 9, 1), date(2026, 9, 30))),
    ],
)
def test_misma_fecha_del_mes_anterior(mes, corte, esperado):
    assert analitica.misma_fecha_mes_anterior(mes, corte) == esperado
