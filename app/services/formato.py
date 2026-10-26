"""Formatos en español para la interfaz (RNF-19) y la fecha de hoy en America/Lima.

Los nombres de días y meses están en tablas propias para no depender del
locale del sistema operativo.
"""
import re
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

ZONA_LIMA = ZoneInfo("America/Lima")

DIAS_CORTOS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
MESES = (
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
)
MESES_CORTOS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")

COLOR_TEXTO_OSCURO = "#111827"
COLOR_TEXTO_CLARO = "#FFFFFF"
_PATRON_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def ahora_lima() -> datetime:
    return datetime.now(ZONA_LIMA)


def hoy_lima() -> date:
    """Fecha de hoy en America/Lima (RN-04)."""
    return ahora_lima().date()


def soles(valor) -> str:
    """1234.5 → 'S/ 1,234.50'."""
    monto = Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    signo = "-" if monto < 0 else ""
    return f"{signo}S/ {abs(monto):,.2f}"


def _en_lima(valor: date | datetime) -> date | datetime:
    if isinstance(valor, datetime) and valor.tzinfo is not None:
        return valor.astimezone(ZONA_LIMA)
    return valor


def fecha(valor: date | datetime | None) -> str:
    """date(2026, 10, 26) → '26/10/2026'."""
    if valor is None:
        return ""
    valor = _en_lima(valor)
    return f"{valor.day:02d}/{valor.month:02d}/{valor.year}"


def fecha_corta(valor: date | datetime | None) -> str:
    """date(2026, 10, 26) → 'lun, 26 oct'."""
    if valor is None:
        return ""
    valor = _en_lima(valor)
    return f"{DIAS_CORTOS[valor.weekday()]}, {valor.day} {MESES_CORTOS[valor.month - 1]}"


def mes_anio(valor: date | datetime | None) -> str:
    """date(2026, 10, 1) → 'Octubre 2026'."""
    if valor is None:
        return ""
    valor = _en_lima(valor)
    return f"{MESES[valor.month - 1]} {valor.year}"


def _luminancia(color_hex: str) -> float:
    """Luminancia relativa según WCAG 2.x."""
    canales = (int(color_hex[i:i + 2], 16) / 255 for i in (1, 3, 5))
    rojo, verde, azul = (
        c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in canales
    )
    return 0.2126 * rojo + 0.7152 * verde + 0.0722 * azul


def _contraste(luminancia_a: float, luminancia_b: float) -> float:
    mayor, menor = max(luminancia_a, luminancia_b), min(luminancia_a, luminancia_b)
    return (mayor + 0.05) / (menor + 0.05)


def color_texto(color_fondo: str) -> str:
    """Color de texto (#111827 o #FFFFFF) con mejor contraste sobre el fondo dado."""
    if not color_fondo or not _PATRON_HEX.match(color_fondo):
        return COLOR_TEXTO_OSCURO
    fondo = _luminancia(color_fondo)
    contraste_oscuro = _contraste(fondo, _luminancia(COLOR_TEXTO_OSCURO))
    contraste_claro = _contraste(fondo, _luminancia(COLOR_TEXTO_CLARO))
    return COLOR_TEXTO_OSCURO if contraste_oscuro >= contraste_claro else COLOR_TEXTO_CLARO
