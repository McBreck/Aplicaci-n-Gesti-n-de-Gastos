"""Montos y porcentajes con el mismo redondeo en toda la app ("mitad hacia arriba")."""
from decimal import Decimal

from app.services.calculo import a_soles, porcentaje_de


def test_a_soles():
    assert a_soles(Decimal("1.005")) == Decimal("1.01")
    assert a_soles(1866.8000000000002) == Decimal("1866.80")
    assert a_soles(0) == Decimal("0.00")


def test_porcentaje_redondea_mitad_hacia_arriba():
    assert porcentaje_de(Decimal("79.65"), 100) == 79.7  # round() de Python daría 79.6
    assert porcentaje_de(1, 8) == 12.5
    assert porcentaje_de(8, 12) == 66.7
    assert porcentaje_de(1, 3, decimales=2) == 33.33
    assert porcentaje_de(5, 0) is None
