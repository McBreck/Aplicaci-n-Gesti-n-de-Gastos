"""PresupuestoService: presupuesto mensual por categoría, comparación y alertas.

Requisitos: RF-12 a RF-14 (CU-10). Reglas: RN-05, RN-06 y RN-10.
"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, or_, select

from app.extensions import db
from app.models import Categoria, Gasto, Presupuesto
from app.models.presupuesto import ESTADO_EN_ALERTA, ESTADO_EXCEDIDA, estado_presupuesto
from app.services import auditoria
from app.services.calculo import porcentaje_de
from app.services.formato import mes_anio
from app.services.periodo import mes_anterior, texto_mes, ultimo_dia
from app.services.validacion import ErrorValidacion, interpretar_monto

ENTIDAD = "presupuesto"
# Restricción CHECK de la tabla presupuesto (EDT 2.2)
ANIO_MINIMO = 2026
ANIO_MAXIMO = 2100
MENSAJE_PERIODO = "El presupuesto se puede definir desde enero de 2026 hasta diciembre de 2100."
ESCALA_BARRA = 125  # la barra muestra hasta el 125 % (sección 11.4)
CERO = Decimal("0.00")


class ErrorPresupuesto(Exception):
    """Error de negocio con un mensaje listo para mostrar al usuario."""


def periodo_editable(mes: date) -> bool:
    return ANIO_MINIMO <= mes.year <= ANIO_MAXIMO


def _porcentaje(ejecutado: Decimal, planificado: Decimal) -> float | None:
    return porcentaje_de(ejecutado, planificado)


@dataclass(frozen=True)
class FilaPresupuesto:
    """Una categoría en el mes: lo planificado (None = sin presupuesto) y lo ejecutado (A7)."""

    categoria: Categoria
    planificado: Decimal | None
    ejecutado: Decimal

    @property
    def tiene_presupuesto(self) -> bool:
        return self.planificado is not None

    @property
    def porcentaje(self) -> float | None:
        return _porcentaje(self.ejecutado, self.planificado) if self.tiene_presupuesto else None

    @property
    def estado(self) -> str | None:
        """RN-05/RN-06: Controlada, En alerta o Excedida (None si no tiene presupuesto)."""
        return estado_presupuesto(self.ejecutado, self.planificado) if self.tiene_presupuesto else None

    @property
    def porcentaje_barra(self) -> float:
        if not self.tiene_presupuesto:
            return 0.0
        if self.planificado == 0:
            return float(ESCALA_BARRA) if self.ejecutado > 0 else 0.0
        return min(self.porcentaje, float(ESCALA_BARRA))

    @property
    def en_alerta(self) -> bool:
        return self.estado in (ESTADO_EN_ALERTA, ESTADO_EXCEDIDA)


@dataclass(frozen=True)
class ComparacionPresupuesto:
    """Ejecutado vs. planificado de un mes (RF-13) con sus alertas (RF-14)."""

    mes: date
    filas: tuple
    sin_categoria: Decimal
    total_mes: Decimal

    @property
    def con_presupuesto(self) -> list[FilaPresupuesto]:
        return [fila for fila in self.filas if fila.tiene_presupuesto]

    @property
    def tiene_presupuesto(self) -> bool:
        return bool(self.con_presupuesto)

    @property
    def total_planificado(self) -> Decimal:
        return sum((fila.planificado for fila in self.con_presupuesto), CERO)

    @property
    def total_ejecutado(self) -> Decimal:
        """Ejecutado de las categorías con presupuesto."""
        return sum((fila.ejecutado for fila in self.con_presupuesto), CERO)

    @property
    def porcentaje_usado(self) -> float | None:
        """A9 = Σ ejecutado / Σ planificado × 100 (solo categorías con presupuesto)."""
        return _porcentaje(self.total_ejecutado, self.total_planificado)

    @property
    def estado_general(self) -> str | None:
        if not self.tiene_presupuesto:
            return None
        return estado_presupuesto(self.total_ejecutado, self.total_planificado)

    @property
    def porcentaje_barra(self) -> float:
        if not self.tiene_presupuesto:
            return 0.0
        if self.porcentaje_usado is None:
            return float(ESCALA_BARRA) if self.total_ejecutado > 0 else 0.0
        return min(self.porcentaje_usado, float(ESCALA_BARRA))

    @property
    def alertas(self) -> list[FilaPresupuesto]:
        """Categorías En alerta o Excedidas; primero las excedidas (badge de la navegación)."""
        filas = [fila for fila in self.filas if fila.en_alerta]
        return sorted(filas, key=lambda fila: fila.estado != ESTADO_EXCEDIDA)

    @property
    def controladas(self) -> int:
        """RN-05: ejecutado ≤ planificado (incluye las que están En alerta)."""
        return sum(1 for fila in self.con_presupuesto if fila.estado != ESTADO_EXCEDIDA)


def _presupuestos_del_mes(usuario_id: int, mes: date) -> dict[int, Presupuesto]:
    consulta = select(Presupuesto).where(
        Presupuesto.usuario_id == usuario_id, Presupuesto.anio == mes.year, Presupuesto.mes == mes.month
    )
    return {presupuesto.categoria_id: presupuesto for presupuesto in db.session.scalars(consulta)}


def comparar(usuario_id: int, mes: date) -> ComparacionPresupuesto:
    """Planificado y ejecutado por categoría en tres consultas (RNF-01).

    Muestra las categorías activas y las inactivas que tienen presupuesto en el mes.
    """
    mes = mes.replace(day=1)
    presupuestos = _presupuestos_del_mes(usuario_id, mes)
    ejecutado = dict(db.session.execute(
        select(Gasto.categoria_id, func.sum(Gasto.monto))
        .where(
            Gasto.usuario_id == usuario_id,
            Gasto.eliminado.is_(False),
            Gasto.fecha.between(mes, ultimo_dia(mes)),
        )
        .group_by(Gasto.categoria_id)
    ).all())
    categorias = db.session.scalars(
        select(Categoria)
        .where(
            Categoria.usuario_id == usuario_id,
            or_(Categoria.activa.is_(True), Categoria.id.in_(list(presupuestos))),
        )
        .order_by(Categoria.id)
    )
    filas = tuple(
        FilaPresupuesto(
            categoria=categoria,
            planificado=presupuestos[categoria.id].monto if categoria.id in presupuestos else None,
            ejecutado=Decimal(ejecutado.get(categoria.id, CERO)),
        )
        for categoria in categorias
    )
    return ComparacionPresupuesto(
        mes=mes,
        filas=filas,
        sin_categoria=Decimal(ejecutado.get(None, CERO)),
        total_mes=sum((Decimal(total) for total in ejecutado.values()), CERO),
    )


def guardar_presupuesto(usuario, mes: date, montos: dict[int, str]) -> int:
    """CU-10: guarda los montos del mes; vacío = sin presupuesto. Devuelve cuántos cambiaron.

    RN-10: uno por usuario, categoría, mes y año (actualiza si ya existe).
    """
    if not periodo_editable(mes):
        raise ErrorPresupuesto(MENSAJE_PERIODO)
    existentes = _presupuestos_del_mes(usuario.id, mes)
    permitidas = {fila.categoria.id for fila in comparar(usuario.id, mes).filas}

    nuevos, errores = {}, {}
    for id_categoria, texto in montos.items():
        if id_categoria not in permitidas:
            continue
        if not (texto or "").strip():
            nuevos[id_categoria] = None
            continue
        try:
            nuevos[id_categoria] = interpretar_monto(texto, permitir_cero=True)
        except ValueError as error:
            errores[str(id_categoria)] = str(error)
    if errores:
        raise ErrorValidacion(errores)

    anterior, nuevo = {}, {}
    for id_categoria, monto in nuevos.items():
        actual = existentes.get(id_categoria)
        previo = actual.monto if actual else None
        if previo == monto:
            continue
        anterior[str(id_categoria)] = str(previo) if previo is not None else None
        nuevo[str(id_categoria)] = str(monto) if monto is not None else None
        if monto is None:
            db.session.delete(actual)
        elif actual:
            actual.monto = monto
        else:
            db.session.add(Presupuesto(
                usuario_id=usuario.id, categoria_id=id_categoria, anio=mes.year, mes=mes.month, monto=monto,
            ))
    if nuevo:
        auditoria.registrar(
            auditoria.MODIFICAR, ENTIDAD, usuario_id=usuario.id,
            detalle={"periodo": texto_mes(mes), "anterior": anterior, "nuevo": nuevo},
        )
        db.session.commit()
    return len(nuevo)


def copiar_mes_anterior(usuario, mes: date) -> int:
    """CU-10, flujo alterno 3a: replica los montos del mes anterior en las categorías activas.

    Las categorías que coinciden se reemplazan; las demás del mes destino se conservan.
    """
    if not periodo_editable(mes):
        raise ErrorPresupuesto(MENSAJE_PERIODO)
    origen_mes = mes_anterior(mes)
    origen = list(db.session.scalars(
        select(Presupuesto)
        .join(Categoria, Categoria.id == Presupuesto.categoria_id)
        .where(
            Presupuesto.usuario_id == usuario.id,
            Presupuesto.anio == origen_mes.year,
            Presupuesto.mes == origen_mes.month,
            Categoria.activa.is_(True),
        )
    ))
    if not origen:
        raise ErrorPresupuesto(f"{mes_anio(origen_mes)} no tiene presupuesto para copiar.")

    existentes = _presupuestos_del_mes(usuario.id, mes)
    nuevo = {}
    for presupuesto in origen:
        actual = existentes.get(presupuesto.categoria_id)
        if actual:
            actual.monto = presupuesto.monto
        else:
            db.session.add(Presupuesto(
                usuario_id=usuario.id, categoria_id=presupuesto.categoria_id,
                anio=mes.year, mes=mes.month, monto=presupuesto.monto,
            ))
        nuevo[str(presupuesto.categoria_id)] = str(presupuesto.monto)
    auditoria.registrar(
        auditoria.MODIFICAR, ENTIDAD, usuario_id=usuario.id,
        detalle={"periodo": texto_mes(mes), "copiado_de": texto_mes(origen_mes), "nuevo": nuevo},
    )
    db.session.commit()
    return len(origen)
