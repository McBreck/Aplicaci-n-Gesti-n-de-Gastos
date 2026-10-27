"""Cálculos compartidos: montos en soles y porcentajes con el mismo redondeo en toda la app.

Se usa aritmética decimal con redondeo "mitad hacia arriba" (el de los cálculos
a mano) para que P-05, el listado, el dashboard y los reportes coincidan.
"""
from decimal import ROUND_HALF_UP, Decimal

CENTIMO = Decimal("0.01")


def a_soles(valor) -> Decimal:
    """Valor (Decimal, int o float de una suma de montos) → Decimal con dos decimales."""
    if isinstance(valor, Decimal):
        return valor.quantize(CENTIMO, rounding=ROUND_HALF_UP)
    # Una suma en float de montos con dos decimales solo difiere en ~1e-12 del valor exacto
    return Decimal(str(round(float(valor), 2))).quantize(CENTIMO, rounding=ROUND_HALF_UP)


def porcentaje_de(parte, total, decimales: int = 1) -> float | None:
    """parte / total × 100 redondeado; None si el total es cero."""
    parte, total = Decimal(str(parte)), Decimal(str(total))
    if total == 0:
        return None
    paso = Decimal(1).scaleb(-decimales)
    return float((parte / total * 100).quantize(paso, rounding=ROUND_HALF_UP))
