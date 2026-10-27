"""ProyeccionService: proyección del gasto al cierre del mes (P1, RF-17, RN-07).

ŷ(d) = b0 + b1·d con d = 1..día de corte e y = gasto acumulado al día d;
b1, b0 = numpy.polyfit(d, y, 1) y P = b0 + b1·D, con D = días del mes.
Se presenta como "Estimación al ritmo actual", nunca como un valor seguro.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Sequence

import numpy as np

from app.services.calculo import a_soles

MIN_DIAS_CON_REGISTROS = 7
MIN_REGISTROS = 10
MENSAJE_ESTIMACION = "Estimación al ritmo actual"
MENSAJE_INSUFICIENTE = "Datos insuficientes para proyectar"


@dataclass(frozen=True)
class Proyeccion:
    suficiente: bool
    valor: Decimal | None = None  # P: gasto estimado al cierre del mes
    b1: float | None = None
    b0: float | None = None
    dia_corte: int | None = None
    dias_mes: int | None = None

    @property
    def mensaje(self) -> str:
        return MENSAJE_ESTIMACION if self.suficiente else MENSAJE_INSUFICIENTE

    def estimado(self, dia: int) -> float:
        return self.b0 + self.b1 * dia

    def linea(self) -> list[tuple[int, float]]:
        """Recta estimada desde el día de corte hasta fin de mes (línea punteada del gráfico)."""
        if not self.suficiente:
            return []
        return [(dia, round(self.estimado(dia), 2)) for dia in range(self.dia_corte, self.dias_mes + 1)]


def es_suficiente(dias_con_registros: int, registros: int) -> bool:
    """RN-07: al menos 7 días con registros y 10 registros en el mes."""
    return dias_con_registros >= MIN_DIAS_CON_REGISTROS and registros >= MIN_REGISTROS


def dia_de_corte(mes: date, hoy: date, ultimo_con_datos: date | None) -> int | None:
    """Último día que se usa: hoy en el mes en curso; el último día con datos si el mes ya pasó."""
    if (mes.year, mes.month) == (hoy.year, hoy.month):
        return hoy.day
    if mes.replace(day=1) < hoy.replace(day=1) and ultimo_con_datos is not None:
        return ultimo_con_datos.day
    return None  # mes futuro o sin datos


def ajustar_recta(acumulado: Sequence[float]) -> tuple[float, float]:
    """Regresión lineal del acumulado sobre d = 1..n. Devuelve (b1, b0)."""
    dias = np.arange(1, len(acumulado) + 1)
    b1, b0 = np.polyfit(dias, np.asarray(acumulado, dtype=float), 1)
    return float(b1), float(b0)


def proyectar(acumulado: Sequence[float], dias_mes: int) -> Proyeccion:
    """P = b0 + b1·D a partir del acumulado de los días 1..n."""
    b1, b0 = ajustar_recta(acumulado)
    return Proyeccion(
        suficiente=True,
        valor=a_soles(b0 + b1 * dias_mes),
        b1=b1,
        b0=b0,
        dia_corte=len(acumulado),
        dias_mes=dias_mes,
    )


def proyectar_mes(acumulado: Sequence[float], *, dias_con_registros: int, registros: int, dias_mes: int) -> Proyeccion:
    """Proyección solo si hay datos suficientes (RN-07); si no, "Datos insuficientes para proyectar"."""
    if not es_suficiente(dias_con_registros, registros) or len(acumulado) < 2:
        return Proyeccion(suficiente=False)
    return proyectar(acumulado, dias_mes)
