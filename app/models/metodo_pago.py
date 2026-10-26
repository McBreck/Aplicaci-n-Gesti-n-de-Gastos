"""Modelo MetodoPago: catálogo fijo cargado por la migración inicial (RN-12)."""
from sqlalchemy import SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db


class MetodoPago(db.Model):
    __tablename__ = "metodo_pago"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)
    nombre: Mapped[str] = mapped_column(String(30), unique=True)

    def __repr__(self) -> str:
        return f"<MetodoPago {self.id} {self.nombre}>"
