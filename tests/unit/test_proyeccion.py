"""ProyeccionService (P1, RF-17, RN-07) con los datos de verificación de la sección 9."""
from datetime import date
from decimal import Decimal

import pytest

from app.services import proyeccion
from tests.datos_verificacion import ACUMULADO_25_DIAS


def test_regresion_con_los_datos_de_verificacion():
    b1, b0 = proyeccion.ajustar_recta(ACUMULADO_25_DIAS)
    assert (round(b1, 4), round(b0, 4)) == (156.2955, 27.8672)


def test_proyeccion_al_cierre_de_un_mes_de_31_dias():
    resultado = proyeccion.proyectar(ACUMULADO_25_DIAS, dias_mes=31)
    assert resultado.suficiente
    assert resultado.valor == Decimal("4873.03")
    assert resultado.mensaje == "Estimación al ritmo actual"
    linea = resultado.linea()
    assert [dia for dia, _ in linea] == list(range(25, 32))
    assert linea[-1][1] == 4873.03


@pytest.mark.parametrize(("dias", "registros", "suficiente"), [(7, 10, True), (6, 10, False), (7, 9, False), (6, 9, False)])
def test_rn07_datos_minimos(dias, registros, suficiente):
    assert proyeccion.es_suficiente(dias, registros) is suficiente
    resultado = proyeccion.proyectar_mes(ACUMULADO_25_DIAS, dias_con_registros=dias, registros=registros, dias_mes=31)
    assert resultado.suficiente is suficiente
    if not suficiente:
        assert resultado.mensaje == "Datos insuficientes para proyectar"
        assert resultado.valor is None and resultado.linea() == []


def test_dia_de_corte():
    hoy = date(2026, 10, 26)
    assert proyeccion.dia_de_corte(date(2026, 10, 1), hoy, date(2026, 10, 9)) == 26
    assert proyeccion.dia_de_corte(date(2026, 9, 1), hoy, date(2026, 9, 28)) == 28  # último día con datos
    assert proyeccion.dia_de_corte(date(2026, 9, 1), hoy, None) is None
    assert proyeccion.dia_de_corte(date(2026, 11, 1), hoy, None) is None
