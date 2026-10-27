"""Modelo Presupuesto mensual por categoría con los estados de RN-05 y RN-06."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    SmallInteger,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.categoria import Categoria

ESTADO_CONTROLADA = "Controlada"
ESTADO_EN_ALERTA = "En alerta"
ESTADO_EXCEDIDA = "Excedida"
UMBRAL_ALERTA = Decimal("0.80")


def estado_presupuesto(ejecutado, planificado) -> str:
    """RN-05/RN-06: Excedida si supera lo planificado; En alerta desde el 80 % hasta el 100 %."""
    ejecutado = Decimal(str(ejecutado))
    planificado = Decimal(str(planificado))
    if ejecutado > planificado:
        return ESTADO_EXCEDIDA
    if planificado > 0 and ejecutado >= planificado * UMBRAL_ALERTA:
        return ESTADO_EN_ALERTA
    return ESTADO_CONTROLADA


class Presupuesto(db.Model):
    __tablename__ = "presupuesto"
    __table_args__ = (
        CheckConstraint("anio BETWEEN 2026 AND 2100", name="anio"),
        CheckConstraint("mes BETWEEN 1 AND 12", name="mes"),
        CheckConstraint("monto >= 0", name="monto_no_negativo"),
        # RN-10: uno por usuario, categoría, mes y año
        UniqueConstraint("usuario_id", "categoria_id", "anio", "mes", name="uq_presupuesto"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categoria.id"))
    anio: Mapped[int] = mapped_column(SmallInteger)
    mes: Mapped[int] = mapped_column(SmallInteger)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    categoria: Mapped[Categoria] = relationship()

    def estado(self, ejecutado) -> str:
        return estado_presupuesto(ejecutado, self.monto)

    def __repr__(self) -> str:
        return f"<Presupuesto {self.anio}-{self.mes:02d} categoria={self.categoria_id} {self.monto}>"
