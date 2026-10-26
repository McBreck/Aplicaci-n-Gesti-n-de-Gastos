"""Modelo Categoria: plantilla predeterminada (usuario_id NULL) y categorías de cada cuenta."""
from datetime import datetime

from sqlalchemy import CHAR, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db

COLOR_POR_DEFECTO = "#8B7BFF"
LONGITUD_NOMBRE = 60

# Paleta de categorías (sección 11.1, cambio CR-01): color y nombre para lectores de pantalla
PALETA = (
    ("#8B7BFF", "Morado"),
    ("#FFD166", "Amarillo"),
    ("#7EF0C0", "Verde menta"),
    ("#93C5FD", "Azul"),
    ("#F9A8D4", "Rosado"),
    ("#FDBA74", "Naranja"),
    ("#BEF264", "Verde lima"),
    ("#67E8F9", "Celeste"),
    ("#CBD5E1", "Gris"),
    ("#C4B5FD", "Lila"),
)


class Categoria(db.Model):
    __tablename__ = "categoria"

    id: Mapped[int] = mapped_column(primary_key=True)
    # NULL = fila de la plantilla predeterminada (RN-11)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(60))
    # TRUE si se copió de la plantilla: no se puede renombrar (RF-11)
    predeterminada: Mapped[bool] = mapped_column(server_default=text("false"))
    color: Mapped[str] = mapped_column(CHAR(7), server_default=COLOR_POR_DEFECTO)
    activa: Mapped[bool] = mapped_column(server_default=text("true"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Categoria {self.id} {self.nombre}>"


# Nombre único sin distinguir mayúsculas: por cuenta y dentro de la plantilla
Index(
    "uq_categoria_usuario_nombre",
    Categoria.usuario_id,
    func.lower(Categoria.nombre),
    unique=True,
    postgresql_where=Categoria.usuario_id.is_not(None),
)
Index(
    "uq_categoria_predeterminada",
    func.lower(Categoria.nombre),
    unique=True,
    postgresql_where=Categoria.usuario_id.is_(None),
)
