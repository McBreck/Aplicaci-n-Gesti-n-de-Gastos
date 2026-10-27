"""Validaciones compartidas: montos en soles (RN-03) y errores por campo."""
from decimal import Decimal

import pytest

from app.services.validacion import MENSAJE_MONTO_INVALIDO, ErrorValidacion, interpretar_monto


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("15.50", "15.50"),
        ("15,50", "15.50"),
        ("15,5", "15.50"),
        ("1,234.56", "1234.56"),
        ("1,234,567", "1234567.00"),
        ("S/ 20", "20.00"),
        (" 7 ", "7.00"),
        (".5", "0.50"),
        ("+3", "3.00"),
        ("99999999.99", "99999999.99"),
    ],
)
def test_montos_aceptados(texto, esperado):
    monto = interpretar_monto(texto)
    assert monto == Decimal(esperado) and monto.as_tuple().exponent == -2


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        (None, "Escribe el monto del gasto."),
        ("  ", "Escribe el monto del gasto."),
        ("abc", MENSAJE_MONTO_INVALIDO),
        ("1.2.3", MENSAJE_MONTO_INVALIDO),
        ("12,3456", MENSAJE_MONTO_INVALIDO),
        ("0", "El monto debe ser mayor que cero."),
        ("-5", "El monto debe ser mayor que cero."),
        ("15.555", "El monto puede tener hasta dos decimales."),
        ("100000000", "El monto no puede ser mayor que S/ 99,999,999.99."),
    ],
)
def test_montos_rechazados(texto, mensaje):
    with pytest.raises(ValueError) as error:
        interpretar_monto(texto)
    assert str(error.value) == mensaje


def test_presupuesto_admite_cero_pero_no_negativos():
    assert interpretar_monto("0", permitir_cero=True) == Decimal("0.00")
    assert interpretar_monto("-0", permitir_cero=True) == Decimal("0.00")
    with pytest.raises(ValueError, match="no puede ser negativo"):
        interpretar_monto("-1", permitir_cero=True)
    with pytest.raises(ValueError, match="^Escribe el monto.$"):
        interpretar_monto("", permitir_cero=True)


def test_error_de_validacion_por_campo():
    error = ErrorValidacion({"monto": "Escribe el monto del gasto.", "fecha": "La fecha no puede ser futura."})
    assert error.errores["fecha"] == "La fecha no puede ser futura."
    assert str(error) == "Escribe el monto del gasto.; La fecha no puede ser futura."
