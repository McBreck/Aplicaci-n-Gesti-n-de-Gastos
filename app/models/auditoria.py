"""Modelo Auditoria: bitácora de eventos (RNF-12). Nunca guarda contraseñas."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class Auditoria(db.Model):
    __tablename__ = "auditoria"
    __table_args__ = (Index("ix_auditoria_usuario_fecha", "usuario_id", "creado_en"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="SET NULL"))
    # INICIO_SESION, CIERRE_SESION, LOGIN_FALLIDO, CREAR, MODIFICAR, ELIMINAR,
    # ACTIVAR, DESACTIVAR, RESTABLECER
    accion: Mapped[str] = mapped_column(String(20))
    entidad: Mapped[str] = mapped_column(String(30))
    entidad_id: Mapped[int | None] = mapped_column(BigInteger)
    # Valores anteriores y nuevos
    detalle: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(INET)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Auditoria {self.id} {self.accion} {self.entidad}>"
