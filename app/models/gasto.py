"""Modelo Gasto con la regla de completitud RN-01."""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
    event,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db
from app.models.categoria import Categoria
from app.models.metodo_pago import MetodoPago

# RN-01: (atributo, relación equivalente, nombre que ve el usuario)
CAMPOS_COMPLETITUD = (
    ("fecha", None, "fecha"),
    ("monto", None, "monto"),
    ("categoria_id", "categoria", "categoría"),
    ("descripcion", None, "descripción"),
    ("metodo_pago_id", "metodo_pago", "método de pago"),
)


class Gasto(db.Model):
    __tablename__ = "gasto"
    __table_args__ = (
        CheckConstraint("monto > 0", name="monto_positivo"),
        Index(
            "ix_gasto_usuario_fecha",
            "usuario_id",
            "fecha",
            postgresql_where=text("eliminado = false"),
        ),
        Index(
            "ix_gasto_usuario_categoria",
            "usuario_id",
            "categoria_id",
            postgresql_where=text("eliminado = false"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    categoria_id: Mapped[int | None] = mapped_column(ForeignKey("categoria.id"))
    metodo_pago_id: Mapped[int | None] = mapped_column(SmallInteger, ForeignKey("metodo_pago.id"))
    fecha: Mapped[date]
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    descripcion: Mapped[str | None] = mapped_column(String(255))
    es_completo: Mapped[bool] = mapped_column(server_default=text("false"))
    # RN-09: eliminación lógica
    eliminado: Mapped[bool] = mapped_column(server_default=text("false"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    categoria: Mapped[Categoria | None] = relationship()
    metodo_pago: Mapped[MetodoPago | None] = relationship()

    def campos_faltantes(self) -> list[str]:
        """Nombres, en lenguaje del usuario, de los campos de RN-01 que están vacíos."""
        faltantes = []
        for atributo, relacion, etiqueta in CAMPOS_COMPLETITUD:
            valor = getattr(self, atributo)
            if valor is None and relacion:
                valor = getattr(self, relacion)
            if valor is None or (isinstance(valor, str) and not valor.strip()):
                faltantes.append(etiqueta)
        return faltantes

    def evaluar_completitud(self) -> bool:
        """Recalcula y devuelve es_completo (RN-01, decisión D-04)."""
        self.es_completo = not self.campos_faltantes()
        return self.es_completo

    def __repr__(self) -> str:
        return f"<Gasto {self.id} {self.fecha} {self.monto}>"


@event.listens_for(Gasto, "before_insert")
@event.listens_for(Gasto, "before_update")
def _recalcular_completitud(_mapper, _conexion, gasto: Gasto) -> None:
    """D-04: es_completo se recalcula siempre al crear o modificar."""
    gasto.evaluar_completitud()
