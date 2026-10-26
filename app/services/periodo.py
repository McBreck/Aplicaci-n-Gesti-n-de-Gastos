"""Meses del calendario: lectura de ?mes=AAAA-MM y límites de cada mes."""
import calendar
from datetime import date, timedelta

ANIO_MINIMO_LECTURA = 2000
ANIO_MAXIMO_LECTURA = 2100


def interpretar_mes(texto: str | None, hoy: date) -> date:
    """'2026-10' → date(2026, 10, 1). Un valor vacío o inválido devuelve el mes de hoy."""
    try:
        anio, mes = (int(parte) for parte in (texto or "").strip().split("-"))
        if not ANIO_MINIMO_LECTURA <= anio <= ANIO_MAXIMO_LECTURA:
            raise ValueError
        return date(anio, mes, 1)
    except ValueError:
        return hoy.replace(day=1)


def texto_mes(mes: date) -> str:
    """date(2026, 10, 1) → '2026-10' (formato de ?mes=)."""
    return f"{mes.year:04d}-{mes.month:02d}"


def ultimo_dia(mes: date) -> date:
    return mes.replace(day=calendar.monthrange(mes.year, mes.month)[1])


def mes_anterior(mes: date) -> date:
    return (mes.replace(day=1) - timedelta(days=1)).replace(day=1)


def mes_siguiente(mes: date) -> date:
    return ultimo_dia(mes) + timedelta(days=1)
