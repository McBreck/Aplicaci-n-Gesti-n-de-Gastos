"""Meses del calendario: lectura de ?mes=AAAA-MM y límites de cada mes."""
from datetime import date

import pytest

from app.services import periodo

HOY = date(2026, 10, 26)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("2026-10", date(2026, 10, 1)),
        (" 2027-01 ", date(2027, 1, 1)),
        ("2000-01", date(2000, 1, 1)),
        # Vacío, inválido o fuera de 2000–2100: el mes de hoy
        (None, date(2026, 10, 1)),
        ("", date(2026, 10, 1)),
        ("octubre", date(2026, 10, 1)),
        ("2026-13", date(2026, 10, 1)),
        ("2026-10-05", date(2026, 10, 1)),
        ("1999-12", date(2026, 10, 1)),
        ("2101-01", date(2026, 10, 1)),
    ],
)
def test_interpretar_mes(texto, esperado):
    assert periodo.interpretar_mes(texto, HOY) == esperado


def test_texto_y_limites_del_mes():
    assert periodo.texto_mes(date(2026, 3, 1)) == "2026-03"
    assert periodo.ultimo_dia(date(2026, 2, 10)) == date(2026, 2, 28)
    assert periodo.ultimo_dia(date(2028, 2, 1)) == date(2028, 2, 29)  # año bisiesto
    assert periodo.mes_anterior(date(2026, 1, 15)) == date(2025, 12, 1)
    assert periodo.mes_siguiente(date(2026, 12, 1)) == date(2027, 1, 1)
    assert periodo.mes_siguiente(date(2026, 10, 1)) == date(2026, 11, 1)
