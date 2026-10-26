"""GastoService: registro, modificación, eliminación lógica, consulta con filtros y completitud.

Requisitos: RF-05 a RF-10. Reglas: RN-01 a RN-04 y RN-09.
"""
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from itertools import groupby

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import Gasto, MetodoPago
from app.services import auditoria
from app.services.calculo import porcentaje_de
from app.services.categoria import obtener_categoria
from app.services.formato import fecha_corta, hoy_lima
from app.services.validacion import ErrorValidacion, interpretar_monto  # noqa: F401  (parte de la API del servicio)

ENTIDAD = "gasto"
LONGITUD_DESCRIPCION = 255
LONGITUD_BUSQUEDA = 100
POR_PAGINA = 50
# Valor de los filtros "Sin categoría" y "Sin registrar"
SIN_VALOR = "sin"
ESTADOS_FILTRO = ("completo", "incompleto")
# Campos que pueden faltar (fecha y monto son obligatorios), en orden de desempate
CAMPOS_OPCIONALES = ("categoría", "descripción", "método de pago")

# Búsqueda sin distinguir tildes (no requiere la extensión unaccent)
_CON_TILDE = "áéíóúüñÁÉÍÓÚÜÑ"
_SIN_TILDE = "aeiouunAEIOUUN"


# --- Validación (RN-02, RN-03, RN-04); el monto se interpreta en validacion.py ----

def interpretar_fecha(texto: str | None, hoy: date) -> date:
    """RN-04: fecha en formato AAAA-MM-DD o dd/mm/aaaa, no posterior a hoy en Lima."""
    valor = (texto or "").strip()
    if not valor:
        raise ValueError("Elige la fecha del gasto.")
    try:
        fecha_gasto = date.fromisoformat(valor)
    except ValueError:
        try:
            fecha_gasto = datetime.strptime(valor, "%d/%m/%Y").date()
        except ValueError as error:
            raise ValueError("Escribe una fecha válida, por ejemplo 26/10/2026.") from error
    if fecha_gasto > hoy:
        raise ValueError("La fecha no puede ser posterior a hoy.")
    return fecha_gasto


def _entero(texto) -> int | None:
    texto = (texto or "").strip()
    return int(texto) if texto.isdigit() else None


def _validar_categoria(usuario_id: int, texto, categoria_actual_id: int | None) -> int | None:
    if not (texto or "").strip():
        return None
    id_categoria = _entero(texto)
    categoria = obtener_categoria(usuario_id, id_categoria) if id_categoria else None
    # Una categoría desactivada solo se acepta si el gasto ya la tenía (RF-11)
    if categoria is None or (not categoria.activa and categoria.id != categoria_actual_id):
        raise ValueError("Elige una de tus categorías.")
    return categoria.id


def _validar_metodo(texto) -> int | None:
    if not (texto or "").strip():
        return None
    id_metodo = _entero(texto)
    if id_metodo is None or db.session.get(MetodoPago, id_metodo) is None:
        raise ValueError("Elige un método de pago de la lista.")
    return id_metodo


def validar_datos(usuario_id: int, datos: dict, *, categoria_actual_id: int | None = None, hoy: date | None = None) -> dict:
    """RN-02: solo fecha y monto son obligatorios. Reúne todos los errores a la vez."""
    hoy = hoy or hoy_lima()
    limpios, errores = {}, {}
    validaciones = (
        ("monto", lambda: interpretar_monto(datos.get("monto"))),
        ("fecha", lambda: interpretar_fecha(datos.get("fecha"), hoy)),
        ("categoria_id", lambda: _validar_categoria(usuario_id, datos.get("categoria_id"), categoria_actual_id)),
        ("metodo_pago_id", lambda: _validar_metodo(datos.get("metodo_pago_id"))),
    )
    for campo, validar in validaciones:
        try:
            limpios[campo] = validar()
        except ValueError as error:
            errores[campo] = str(error)

    descripcion = (datos.get("descripcion") or "").strip()
    if len(descripcion) > LONGITUD_DESCRIPCION:
        errores["descripcion"] = f"La descripción puede tener hasta {LONGITUD_DESCRIPCION} caracteres."
    limpios["descripcion"] = descripcion or None

    if errores:
        raise ErrorValidacion(errores)
    return limpios


# --- Registro, modificación y eliminación lógica ---------------------------------

def _instantanea(gasto: Gasto) -> dict:
    """Valores del gasto para la bitácora (serializables en JSON)."""
    return {
        "fecha": gasto.fecha.isoformat(),
        "monto": str(gasto.monto),
        "categoria_id": gasto.categoria_id,
        "metodo_pago_id": gasto.metodo_pago_id,
        "descripcion": gasto.descripcion,
    }


def registrar_gasto(usuario, datos: dict) -> Gasto:
    """CU-05: guarda el gasto; es_completo se calcula al insertar (RN-01, D-04)."""
    limpios = validar_datos(usuario.id, datos)
    gasto = Gasto(usuario_id=usuario.id, **limpios)
    db.session.add(gasto)
    db.session.flush()
    auditoria.registrar(
        auditoria.CREAR, ENTIDAD, usuario_id=usuario.id, entidad_id=gasto.id,
        detalle={"nuevo": _instantanea(gasto)},
    )
    db.session.commit()
    return gasto


def modificar_gasto(gasto: Gasto, usuario, datos: dict) -> Gasto:
    """CU-06: al completar los campos faltantes el gasto pasa a Completo (RF-07)."""
    limpios = validar_datos(usuario.id, datos, categoria_actual_id=gasto.categoria_id)
    anterior = _instantanea(gasto)
    for campo, valor in limpios.items():
        setattr(gasto, campo, valor)
    gasto.evaluar_completitud()
    nuevo = _instantanea(gasto)
    cambios = {campo: valor for campo, valor in nuevo.items() if anterior[campo] != valor}
    if cambios:
        auditoria.registrar(
            auditoria.MODIFICAR, ENTIDAD, usuario_id=usuario.id, entidad_id=gasto.id,
            detalle={"anterior": {campo: anterior[campo] for campo in cambios}, "nuevo": cambios},
        )
    db.session.commit()
    return gasto


def eliminar_gasto(gasto: Gasto, usuario) -> None:
    """CU-07, RN-09: eliminación lógica; queda registrada en la bitácora."""
    gasto.eliminado = True
    auditoria.registrar(
        auditoria.ELIMINAR, ENTIDAD, usuario_id=usuario.id, entidad_id=gasto.id,
        detalle={"anterior": _instantanea(gasto)},
    )
    db.session.commit()


def obtener_gasto_propio(usuario_id: int, id_gasto: int) -> Gasto | None:
    """Gasto vigente del usuario; uno ajeno o eliminado devuelve None (la ruta responde 404)."""
    consulta = (
        select(Gasto)
        .options(joinedload(Gasto.categoria), joinedload(Gasto.metodo_pago))
        .where(Gasto.id == id_gasto, Gasto.usuario_id == usuario_id, Gasto.eliminado.is_(False))
    )
    return db.session.scalar(consulta)


def listar_metodos_pago() -> list[MetodoPago]:
    return list(db.session.scalars(select(MetodoPago).order_by(MetodoPago.id)))


# --- Consulta con filtros (RF-09) ------------------------------------------------

@dataclass(frozen=True)
class FiltrosGastos:
    desde: date | None = None
    hasta: date | None = None
    categoria: str = ""  # "", "sin" o el id
    metodo: str = ""  # "", "sin" o el id
    estado: str = ""  # "", "completo" o "incompleto"
    q: str = ""

    def como_argumentos(self) -> dict:
        """Parámetros de la URL que reproducen este filtro (para la paginación)."""
        argumentos = {
            "desde": self.desde.isoformat() if self.desde else "",
            "hasta": self.hasta.isoformat() if self.hasta else "",
        }
        for nombre in ("categoria", "metodo", "estado", "q"):
            if getattr(self, nombre):
                argumentos[nombre] = getattr(self, nombre)
        return argumentos

    def cantidad_adicionales(self) -> int:
        """Filtros aplicados además de las fechas."""
        return sum(1 for valor in (self.categoria, self.metodo, self.estado, self.q) if valor)


def filtros_por_defecto(hoy: date) -> FiltrosGastos:
    """Mes actual (CU-08)."""
    return FiltrosGastos(desde=hoy.replace(day=1), hasta=hoy)


def _fecha_de_filtro(texto: str, nombre: str, avisos: list[str]) -> date | None:
    if not texto:
        return None
    try:
        return date.fromisoformat(texto)
    except ValueError:
        avisos.append(f"La fecha «{nombre}» no es válida y no se tuvo en cuenta.")
        return None


def interpretar_filtros(argumentos, hoy: date) -> tuple[FiltrosGastos, list[str]]:
    """Lee los filtros de la URL. Sin fechas en la URL se usa el mes actual;
    una fecha enviada vacía significa «sin límite»."""
    avisos: list[str] = []
    por_defecto = filtros_por_defecto(hoy)
    desde = por_defecto.desde
    hasta = por_defecto.hasta
    if "desde" in argumentos:
        desde = _fecha_de_filtro(argumentos.get("desde", "").strip(), "Desde", avisos)
    if "hasta" in argumentos:
        hasta = _fecha_de_filtro(argumentos.get("hasta", "").strip(), "Hasta", avisos)
    if desde and hasta and desde > hasta:
        desde, hasta = hasta, desde
        avisos.append("Intercambiamos las fechas porque «Desde» era posterior a «Hasta».")

    def _id_o_sin(texto: str) -> str:
        texto = (texto or "").strip()
        return texto if texto == SIN_VALOR or texto.isdigit() else ""

    estado = (argumentos.get("estado") or "").strip()
    filtros = FiltrosGastos(
        desde=desde,
        hasta=hasta,
        categoria=_id_o_sin(argumentos.get("categoria")),
        metodo=_id_o_sin(argumentos.get("metodo")),
        estado=estado if estado in ESTADOS_FILTRO else "",
        q=(argumentos.get("q") or "").strip()[:LONGITUD_BUSQUEDA],
    )
    return filtros, avisos


def _sin_tildes(expresion):
    # Primero se quitan las tildes y luego se pasa a minúsculas: lower() sobre letras
    # sin tilde funciona igual con cualquier configuración regional de PostgreSQL
    return func.lower(func.translate(expresion, _CON_TILDE, _SIN_TILDE))


def _texto_sin_tildes(texto: str) -> str:
    return texto.translate(str.maketrans(_CON_TILDE, _SIN_TILDE)).lower()


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _condiciones(usuario_id: int, filtros: FiltrosGastos) -> list:
    """Condiciones de la consulta: siempre del usuario y sin eliminados (RN-09, RNF-09)."""
    condiciones = [Gasto.usuario_id == usuario_id, Gasto.eliminado.is_(False)]
    if filtros.desde:
        condiciones.append(Gasto.fecha >= filtros.desde)
    if filtros.hasta:
        condiciones.append(Gasto.fecha <= filtros.hasta)
    for valor, columna in ((filtros.categoria, Gasto.categoria_id), (filtros.metodo, Gasto.metodo_pago_id)):
        if valor == SIN_VALOR:
            condiciones.append(columna.is_(None))
        elif valor:
            condiciones.append(columna == int(valor))
    if filtros.estado:
        condiciones.append(Gasto.es_completo.is_(filtros.estado == "completo"))
    if filtros.q:
        patron = f"%{_escapar_like(_texto_sin_tildes(filtros.q))}%"
        condiciones.append(_sin_tildes(Gasto.descripcion).like(patron, escape="\\"))
    return condiciones


# --- Completitud (RF-10, métrica A8) --------------------------------------------

@dataclass(frozen=True)
class ResumenGastos:
    cantidad: int = 0
    total: Decimal = Decimal("0.00")
    completos: int = 0
    faltantes: dict = field(default_factory=dict)  # campo → cantidad de gastos sin él

    @property
    def incompletos(self) -> int:
        return self.cantidad - self.completos

    @property
    def porcentaje_completitud(self) -> float | None:
        """A8 = RC / TR × 100 (None si no hay registros)."""
        return porcentaje_de(self.completos, self.cantidad)

    @property
    def campo_mas_omitido(self) -> str | None:
        """Campo con más omisiones; en empate, el primero en el orden de RN-01."""
        candidatos = [(self.faltantes.get(campo, 0), campo) for campo in CAMPOS_OPCIONALES]
        mayor = max((cantidad for cantidad, _ in candidatos), default=0)
        if mayor == 0:
            return None
        return next(campo for cantidad, campo in candidatos if cantidad == mayor)


def resumir(usuario_id: int, filtros: FiltrosGastos) -> ResumenGastos:
    """Total, cantidad y completitud del resultado filtrado en una sola consulta."""
    sin_descripcion = or_(Gasto.descripcion.is_(None), func.trim(Gasto.descripcion) == "")
    fila = db.session.execute(
        select(
            func.count(Gasto.id),
            func.coalesce(func.sum(Gasto.monto), 0),
            func.count(Gasto.id).filter(Gasto.es_completo.is_(True)),
            func.count(Gasto.id).filter(Gasto.categoria_id.is_(None)),
            func.count(Gasto.id).filter(sin_descripcion),
            func.count(Gasto.id).filter(Gasto.metodo_pago_id.is_(None)),
        ).where(*_condiciones(usuario_id, filtros))
    ).one()
    cantidad, total, completos, sin_categoria, sin_desc, sin_metodo = fila
    return ResumenGastos(
        cantidad=cantidad,
        total=Decimal(total).quantize(Decimal("0.01")),
        completos=completos,
        faltantes={"categoría": sin_categoria, "descripción": sin_desc, "método de pago": sin_metodo},
    )


@dataclass(frozen=True)
class PaginaGastos:
    gastos: list
    pagina: int
    total_paginas: int
    resumen: ResumenGastos
    totales_por_dia: dict


def listar_gastos(usuario_id: int, filtros: FiltrosGastos, pagina: int = 1) -> PaginaGastos:
    """CU-08: página de 50 gastos, del más reciente al más antiguo, sin consultas N+1."""
    resumen = resumir(usuario_id, filtros)
    total_paginas = max(1, math.ceil(resumen.cantidad / POR_PAGINA))
    pagina = min(max(1, pagina), total_paginas)
    condiciones = _condiciones(usuario_id, filtros)

    gastos = list(db.session.scalars(
        select(Gasto)
        .options(joinedload(Gasto.categoria), joinedload(Gasto.metodo_pago))
        .where(*condiciones)
        .order_by(Gasto.fecha.desc(), Gasto.id.desc())
        .limit(POR_PAGINA)
        .offset((pagina - 1) * POR_PAGINA)
    ))

    totales_por_dia = {}
    fechas = {gasto.fecha for gasto in gastos}
    if fechas:
        filas = db.session.execute(
            select(Gasto.fecha, func.sum(Gasto.monto))
            .where(*condiciones, Gasto.fecha.in_(fechas))
            .group_by(Gasto.fecha)
        )
        totales_por_dia = {fecha_dia: total for fecha_dia, total in filas}
    return PaginaGastos(gastos, pagina, total_paginas, resumen, totales_por_dia)


# --- Actividad agrupada por fecha (componente `actividad`) ------------------------

@dataclass(frozen=True)
class FilaActividad:
    """Un gasto, o varios de la misma categoría el mismo día ("3 registros")."""

    gastos: tuple
    clave: str

    @property
    def es_grupo(self) -> bool:
        return len(self.gastos) > 1

    @property
    def gasto(self):
        return self.gastos[0]

    @property
    def categoria(self):
        return self.gastos[0].categoria

    @property
    def total(self) -> Decimal:
        return sum((gasto.monto for gasto in self.gastos), Decimal("0"))


@dataclass(frozen=True)
class DiaActividad:
    fecha: date
    etiqueta: str
    total: Decimal
    filas: tuple


def etiqueta_dia(fecha_dia: date, hoy: date) -> str:
    if fecha_dia == hoy:
        return "Hoy"
    if fecha_dia == hoy - timedelta(days=1):
        return "Ayer"
    return fecha_corta(fecha_dia)


def _filas_del_dia(gastos: list, agrupar_categorias: bool) -> tuple:
    if not agrupar_categorias:
        return tuple(FilaActividad((gasto,), f"g{gasto.id}") for gasto in gastos)
    por_categoria: dict = {}
    for gasto in gastos:
        por_categoria.setdefault(gasto.categoria_id, []).append(gasto)
    return tuple(
        FilaActividad(tuple(grupo), f"d{grupo[0].fecha:%Y%m%d}c{grupo[0].categoria_id or 0}")
        for grupo in por_categoria.values()
    )


def agrupar_actividad(gastos: list, hoy: date, totales_por_dia: dict | None = None,
                      agrupar_categorias: bool = False) -> list[DiaActividad]:
    """Agrupa por fecha ("Hoy", "Ayer", "mié, 21 oct") con el total del día.

    Los gastos deben venir ordenados por fecha descendente.
    """
    totales_por_dia = totales_por_dia or {}
    dias = []
    for fecha_dia, del_dia in groupby(gastos, key=lambda gasto: gasto.fecha):
        del_dia = list(del_dia)
        total = totales_por_dia.get(fecha_dia, sum((g.monto for g in del_dia), Decimal("0")))
        dias.append(
            DiaActividad(fecha_dia, etiqueta_dia(fecha_dia, hoy), total, _filas_del_dia(del_dia, agrupar_categorias))
        )
    return dias
