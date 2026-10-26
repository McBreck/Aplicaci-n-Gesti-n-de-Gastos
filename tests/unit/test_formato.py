"""Filtros de formato en español (RNF-19) y contraste de color (sección 11.1)."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from app.services import formato


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (Decimal("1234.56"), "S/ 1,234.56"),
        (1866.8, "S/ 1,866.80"),
        (4873.025, "S/ 4,873.03"),
        (0, "S/ 0.00"),
        (None, "S/ 0.00"),
        (Decimal("99999999.99"), "S/ 99,999,999.99"),
        (Decimal("-5"), "-S/ 5.00"),
    ],
)
def test_soles(valor, esperado):
    assert formato.soles(valor) == esperado


def test_fecha():
    assert formato.fecha(date(2026, 10, 26)) == "26/10/2026"
    assert formato.fecha(date(2026, 1, 5)) == "05/01/2026"
    assert formato.fecha(None) == ""


def test_fecha_convierte_a_hora_de_lima():
    # 03:00 UTC del 27/10 son las 22:00 del 26/10 en Lima (UTC−5)
    instante = datetime(2026, 10, 27, 3, 0, tzinfo=timezone.utc)
    assert formato.fecha(instante) == "26/10/2026"


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (date(2026, 10, 26), "lun, 26 oct"),
        (date(2026, 10, 21), "mié, 21 oct"),
        (date(2026, 10, 22), "jue, 22 oct"),
        (date(2026, 11, 1), "dom, 1 nov"),
        (date(2026, 10, 31), "sáb, 31 oct"),
    ],
)
def test_fecha_corta(valor, esperado):
    assert formato.fecha_corta(valor) == esperado


def test_mes_anio():
    assert formato.mes_anio(date(2026, 10, 1)) == "Octubre 2026"
    assert formato.mes_anio(date(2027, 1, 15)) == "Enero 2027"
    assert formato.mes_anio(None) == ""


def test_hoy_lima_usa_la_zona_de_lima():
    assert formato.ahora_lima().utcoffset().total_seconds() == -5 * 3600
    assert formato.hoy_lima() == formato.ahora_lima().date()


@pytest.mark.parametrize(
    "color",
    ["#8B7BFF", "#FFD166", "#7EF0C0", "#93C5FD", "#F9A8D4",
     "#FDBA74", "#BEF264", "#67E8F9", "#CBD5E1", "#C4B5FD"],
)
def test_color_texto_oscuro_sobre_la_paleta(color):
    assert formato.color_texto(color) == "#111827"


@pytest.mark.parametrize("color", ["#000000", "#1E3A8A", "#7F1D1D"])
def test_color_texto_blanco_sobre_colores_oscuros(color):
    assert formato.color_texto(color) == "#FFFFFF"


@pytest.mark.parametrize("color", [None, "", "rojo", "#FFF", "#GGGGGG"])
def test_color_texto_con_valor_invalido(color):
    assert formato.color_texto(color) == "#111827"
