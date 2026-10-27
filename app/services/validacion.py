"""Validaciones compartidas por los servicios (montos en soles y errores por campo)."""
import re
from decimal import Decimal, InvalidOperation

MONTO_MAXIMO = Decimal("99999999.99")
MENSAJE_MONTO_INVALIDO = "Escribe el monto solo con números, por ejemplo 15.50."
_PATRON_NUMERO = re.compile(r"^(\d+(\.\d*)?|\.\d+)$")
_PATRON_DECIMAL_CON_COMA = re.compile(r"^\d+,\d{1,2}$")
_PATRON_MILES_CON_COMA = re.compile(r"^\d{1,3}(,\d{3})+(\.\d*)?$")


class ErrorValidacion(Exception):
    """Datos inválidos: errores por campo, con mensajes para el usuario."""

    def __init__(self, errores: dict[str, str]):
        super().__init__("; ".join(errores.values()))
        self.errores = errores


def interpretar_monto(texto: str | None, *, permitir_cero: bool = False) -> Decimal:
    """RN-03: acepta '15.50', '15,50', '1,234.56' y 'S/ 20'. Lanza ValueError con el mensaje.

    El gasto exige un monto mayor que cero; el presupuesto admite cero (permitir_cero).
    """
    valor = (texto or "").replace("S/", "").replace(" ", "").strip()
    if not valor:
        raise ValueError("Escribe el monto del gasto." if not permitir_cero else "Escribe el monto.")
    negativo = valor.startswith("-")
    valor = valor.lstrip("+-")
    if _PATRON_MILES_CON_COMA.match(valor):
        valor = valor.replace(",", "")
    elif _PATRON_DECIMAL_CON_COMA.match(valor):
        valor = valor.replace(",", ".")
    if not _PATRON_NUMERO.match(valor):
        raise ValueError(MENSAJE_MONTO_INVALIDO)
    try:
        monto = Decimal(valor)
    except InvalidOperation as error:
        raise ValueError(MENSAJE_MONTO_INVALIDO) from error
    if permitir_cero:
        if negativo and monto != 0:
            raise ValueError("El monto no puede ser negativo.")
    elif negativo or monto <= 0:
        raise ValueError("El monto debe ser mayor que cero.")
    if monto != monto.quantize(Decimal("0.01")):
        raise ValueError("El monto puede tener hasta dos decimales.")
    if monto > MONTO_MAXIMO:
        raise ValueError("El monto no puede ser mayor que S/ 99,999,999.99.")
    return monto.quantize(Decimal("0.01"))
