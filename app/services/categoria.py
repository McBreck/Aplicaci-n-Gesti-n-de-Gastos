"""CategoriaService: categorías predeterminadas y propias (RF-11).

En la EDT 3.3 solo incluye las consultas que necesita el registro de gastos;
la gestión de categorías (crear, renombrar, activar) se agrega en la EDT 3.4.
"""
from sqlalchemy import or_, select

from app.extensions import db
from app.models import Categoria


def listar_categorias(usuario_id: int, *, solo_activas: bool = True, incluir_id: int | None = None) -> list[Categoria]:
    """Categorías del usuario en el orden de la plantilla.

    incluir_id agrega una categoría inactiva que un gasto ya tiene (RF-11: se
    conserva en el historial y se muestra al editar).
    """
    consulta = select(Categoria).where(Categoria.usuario_id == usuario_id)
    if solo_activas:
        activa = Categoria.activa.is_(True)
        consulta = consulta.where(or_(activa, Categoria.id == incluir_id) if incluir_id else activa)
    return list(db.session.scalars(consulta.order_by(Categoria.id)))


def obtener_categoria(usuario_id: int, id_categoria: int) -> Categoria | None:
    consulta = select(Categoria).where(Categoria.id == id_categoria, Categoria.usuario_id == usuario_id)
    return db.session.scalar(consulta)
