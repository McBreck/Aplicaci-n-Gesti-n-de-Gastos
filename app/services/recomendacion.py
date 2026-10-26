"""RecomendacionService: reglas R1–R7 (RF-18, RN-08).

Funciones puras: reciben los resultados del análisis del mes y devuelven como
máximo tres recomendaciones ordenadas por prioridad. Cada una corresponde a una
regla cuya condición se cumple y lleva un enlace de acción.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.models.presupuesto import ESTADO_EN_ALERTA, ESTADO_EXCEDIDA
from app.services.calculo import porcentaje_de
from app.services.formato import MESES, fecha, porcentaje, soles
from app.services.gasto import ResumenGastos
from app.services.periodo import texto_mes, ultimo_dia
from app.services.proyeccion import Proyeccion

MAXIMO = 3
MENSAJE_BAJO_CONTROL = "Tus gastos están bajo control este mes"
UMBRAL_COMPLETITUD = 80.0
UMBRAL_AUMENTO = 30.0
MONTO_MINIMO_AUMENTO = Decimal("50")
UMBRAL_PARTICIPACION = 20.0
DIAS_SIN_REGISTRO = 3
# Orden de desempate entre reglas con la misma prioridad (R5 y R7 tienen prioridad 5)
ORDEN_REGLAS = ("R2", "R3", "R1", "R4", "R5", "R7", "R6")
ESTADO_INFORMATIVO = "Informativa"


@dataclass(frozen=True)
class EjecucionCategoria:
    """Una fila de A7: categoría con presupuesto en el mes."""

    categoria_id: int
    categoria: str
    planificado: Decimal
    ejecutado: Decimal
    porcentaje: float | None
    estado: str


@dataclass(frozen=True)
class GastoCategoria:
    """Una fila de A3 con lo gastado en el mismo período del mes anterior."""

    categoria_id: int | None  # None = "Sin categoría"
    categoria: str
    total: Decimal
    anterior: Decimal
    participacion: float  # % del total del mes


@dataclass(frozen=True)
class DatosRecomendacion:
    mes: date
    hoy: date
    ejecucion: tuple
    categorias: tuple
    completitud: ResumenGastos
    proyeccion: Proyeccion
    ultima_fecha: date | None = None

    @property
    def total_presupuesto(self) -> Decimal:
        return sum((fila.planificado for fila in self.ejecucion), Decimal("0.00"))

    @property
    def es_mes_en_curso(self) -> bool:
        return (self.mes.year, self.mes.month) == (self.hoy.year, self.hoy.month)

    def periodo(self) -> dict:
        """Fechas del mes para los enlaces a Mis gastos."""
        return {"desde": self.mes.replace(day=1).isoformat(), "hasta": ultimo_dia(self.mes).isoformat()}


@dataclass(frozen=True)
class Recomendacion:
    regla: str
    prioridad: int
    mensaje: str
    accion: str
    endpoint: str
    argumentos: dict = field(default_factory=dict)
    estado: str = ESTADO_INFORMATIVO  # define el color del ícono
    magnitud: float = 0.0  # desempate dentro de la misma regla (mayor primero)


def _r2_categorias_excedidas(datos: DatosRecomendacion):
    for fila in datos.ejecucion:
        if fila.estado != ESTADO_EXCEDIDA:
            continue
        diferencia = fila.ejecutado - fila.planificado
        exceso = porcentaje_de(diferencia, fila.planificado)
        detalle = f" ({porcentaje(exceso)})" if exceso is not None else ""
        yield Recomendacion(
            "R2", 1, f"{fila.categoria} superó su presupuesto en {soles(diferencia)}{detalle}.",
            "Ver gastos de la categoría", "gastos.listar",
            {"categoria": fila.categoria_id, **datos.periodo()}, ESTADO_EXCEDIDA, float(exceso or 0),
        )


def _r3_proyeccion_sobre_presupuesto(datos: DatosRecomendacion):
    proyeccion, total = datos.proyeccion, datos.total_presupuesto
    # Solo en el mes en curso: el mensaje habla del cierre que todavía no ocurre
    if not (datos.es_mes_en_curso and proyeccion.suficiente and total and proyeccion.valor > total):
        return
    exceso = proyeccion.valor - total
    nombre_mes = MESES[datos.mes.month - 1].lower()
    yield Recomendacion(
        "R3", 2,
        f"Al ritmo actual cerrarías {nombre_mes} en {soles(proyeccion.valor)}, "
        f"{soles(exceso)} por encima de tu presupuesto.",
        "Ver presupuesto", "presupuesto.ver", {"mes": texto_mes(datos.mes)}, ESTADO_EXCEDIDA, float(exceso),
    )


def _r1_categorias_en_alerta(datos: DatosRecomendacion):
    for fila in datos.ejecucion:
        if fila.estado == ESTADO_EN_ALERTA:
            yield Recomendacion(
                "R1", 3, f"Has usado el {porcentaje(fila.porcentaje)} del presupuesto de {fila.categoria}.",
                "Ver presupuesto", "presupuesto.ver", {"mes": texto_mes(datos.mes)}, ESTADO_EN_ALERTA,
                float(fila.porcentaje or 0),
            )


def _r4_completitud_baja(datos: DatosRecomendacion):
    completitud = datos.completitud
    if not completitud.cantidad or completitud.porcentaje_completitud >= UMBRAL_COMPLETITUD:
        return
    cantidad = completitud.incompletos
    sujeto = "1 gasto está incompleto" if cantidad == 1 else f"{cantidad} gastos están incompletos"
    yield Recomendacion(
        "R4", 4, f"{sujeto}; el dato más omitido es {completitud.campo_mas_omitido}.",
        "Ver gastos incompletos", "gastos.listar", {"estado": "incompleto", **datos.periodo()}, ESTADO_EN_ALERTA,
        float(cantidad),
    )


def _r5_aumento_frente_al_mes_anterior(datos: DatosRecomendacion):
    for categoria in datos.categorias:
        if categoria.categoria_id is None or categoria.total < MONTO_MINIMO_AUMENTO or not categoria.anterior:
            continue
        aumento = porcentaje_de(categoria.total - categoria.anterior, categoria.anterior)
        if aumento > UMBRAL_AUMENTO:
            yield Recomendacion(
                "R5", 5, f"Tus gastos en {categoria.categoria} subieron {porcentaje(aumento)} respecto al mes pasado.",
                "Ver gastos de la categoría", "gastos.listar",
                {"categoria": categoria.categoria_id, **datos.periodo()}, ESTADO_EN_ALERTA, aumento,
            )


def _r7_categoria_sin_presupuesto(datos: DatosRecomendacion):
    con_presupuesto = {fila.categoria_id for fila in datos.ejecucion}
    for categoria in datos.categorias:
        if (categoria.categoria_id is not None and categoria.categoria_id not in con_presupuesto
                and categoria.participacion > UMBRAL_PARTICIPACION):
            yield Recomendacion(
                "R7", 5,
                f"{categoria.categoria} no tiene presupuesto y representa el {porcentaje(categoria.participacion)} "
                "de tus gastos.",
                "Definir presupuesto", "presupuesto.ver", {"mes": texto_mes(datos.mes)}, ESTADO_INFORMATIVO,
                categoria.participacion,
            )


def _r6_sin_registros_recientes(datos: DatosRecomendacion):
    if not (datos.es_mes_en_curso and datos.ultima_fecha and datos.hoy.day >= DIAS_SIN_REGISTRO):
        return
    if (datos.hoy - datos.ultima_fecha).days >= DIAS_SIN_REGISTRO:
        yield Recomendacion(
            "R6", 6, f"No registras gastos desde el {fecha(datos.ultima_fecha)}. ¿Olvidaste anotar alguno?",
            "Registrar gasto", "gastos.nuevo", {}, ESTADO_INFORMATIVO,
        )


REGLAS = (
    _r2_categorias_excedidas,
    _r3_proyeccion_sobre_presupuesto,
    _r1_categorias_en_alerta,
    _r4_completitud_baja,
    _r5_aumento_frente_al_mes_anterior,
    _r7_categoria_sin_presupuesto,
    _r6_sin_registros_recientes,
)


def generar(datos: DatosRecomendacion, maximo: int = MAXIMO) -> list[Recomendacion]:
    """RN-08: como máximo tres, por prioridad ascendente. Lista vacía = gastos bajo control."""
    candidatas = [recomendacion for regla in REGLAS for recomendacion in regla(datos)]
    candidatas.sort(key=lambda r: (r.prioridad, ORDEN_REGLAS.index(r.regla), -r.magnitud))
    return candidatas[:maximo]
