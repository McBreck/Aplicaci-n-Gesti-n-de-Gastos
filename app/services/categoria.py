"""CategoriaService: categorías predeterminadas y propias (RF-11, CU-09).

Cada cuenta recibe una copia de la plantilla (RN-11); además puede crear y
renombrar categorías propias y activar o desactivar cualquiera. Una categoría
desactivada no aparece al registrar, pero se conserva en el historial.
"""
from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Categoria, Gasto
from app.models.categoria import LONGITUD_NOMBRE, PALETA
from app.services import auditoria

ENTIDAD = "categoria"
MENSAJE_NOMBRE_REPETIDO = "Ya tienes una categoría con ese nombre"
COLORES_PERMITIDOS = {color for color, _ in PALETA}


class ErrorCategoria(Exception):
    """Error de negocio con un mensaje listo para mostrar al usuario."""


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


def mas_usadas(usuario_id: int, hoy: date, *, dias: int = 30, cantidad: int = 3) -> list[Categoria]:
    """Tarjetas rápidas de P-02: las categorías activas con más registros en los últimos 30 días.

    Si no alcanzan, se completan con las primeras categorías activas.
    """
    usos = (
        select(Gasto.categoria_id)
        .join(Categoria, Categoria.id == Gasto.categoria_id)
        .where(
            Gasto.usuario_id == usuario_id,
            Gasto.eliminado.is_(False),
            Gasto.fecha.between(hoy - timedelta(days=dias - 1), hoy),
            Categoria.activa.is_(True),
        )
        .group_by(Gasto.categoria_id)
        .order_by(func.count(Gasto.id).desc(), func.sum(Gasto.monto).desc(), Gasto.categoria_id)
        .limit(cantidad)
    )
    activas = listar_categorias(usuario_id)
    por_id = {categoria.id: categoria for categoria in activas}
    elegidas = [por_id[id_categoria] for id_categoria in db.session.scalars(usos) if id_categoria in por_id]
    for categoria in activas:
        if len(elegidas) >= cantidad:
            break
        if categoria not in elegidas:
            elegidas.append(categoria)
    return elegidas


def obtener_categoria(usuario_id: int, id_categoria: int) -> Categoria | None:
    consulta = select(Categoria).where(Categoria.id == id_categoria, Categoria.usuario_id == usuario_id)
    return db.session.scalar(consulta)


def _validar_nombre(usuario_id: int, nombre: str, excepto_id: int | None = None) -> str:
    nombre = " ".join((nombre or "").split())
    if not nombre:
        raise ErrorCategoria("Escribe el nombre de la categoría.")
    if len(nombre) > LONGITUD_NOMBRE:
        raise ErrorCategoria(f"El nombre puede tener hasta {LONGITUD_NOMBRE} caracteres.")
    repetida = db.session.scalar(
        select(Categoria.id).where(
            Categoria.usuario_id == usuario_id,
            func.lower(Categoria.nombre) == nombre.lower(),
            Categoria.id != (excepto_id or 0),
        )
    )
    if repetida:
        raise ErrorCategoria(MENSAJE_NOMBRE_REPETIDO)
    return nombre


def crear_categoria(usuario, nombre: str, color: str) -> Categoria:
    nombre = _validar_nombre(usuario.id, nombre)
    color = (color or "").upper()
    if color not in COLORES_PERMITIDOS:
        raise ErrorCategoria("Elige uno de los colores de la paleta.")
    categoria = Categoria(usuario_id=usuario.id, nombre=nombre, color=color, predeterminada=False)
    db.session.add(categoria)
    try:
        db.session.flush()
    except IntegrityError as error:
        # Otra petición creó el mismo nombre al mismo tiempo (índice único sin mayúsculas)
        db.session.rollback()
        raise ErrorCategoria(MENSAJE_NOMBRE_REPETIDO) from error
    auditoria.registrar(
        auditoria.CREAR, ENTIDAD, usuario_id=usuario.id, entidad_id=categoria.id,
        detalle={"nuevo": {"nombre": nombre, "color": color}},
    )
    db.session.commit()
    return categoria


def renombrar_categoria(categoria: Categoria, usuario, nombre: str) -> None:
    """Solo las categorías propias se renombran; las predeterminadas conservan su nombre."""
    if categoria.predeterminada:
        raise ErrorCategoria("Las categorías predeterminadas no se pueden renombrar.")
    nombre = _validar_nombre(usuario.id, nombre, excepto_id=categoria.id)
    if nombre == categoria.nombre:
        return
    anterior = categoria.nombre
    categoria.nombre = nombre
    auditoria.registrar(
        auditoria.MODIFICAR, ENTIDAD, usuario_id=usuario.id, entidad_id=categoria.id,
        detalle={"anterior": {"nombre": anterior}, "nuevo": {"nombre": nombre}},
    )
    db.session.commit()


def cambiar_estado(categoria: Categoria, usuario) -> bool:
    """Activa o desactiva cualquier categoría y devuelve el nuevo estado."""
    categoria.activa = not categoria.activa
    accion = auditoria.ACTIVAR if categoria.activa else auditoria.DESACTIVAR
    auditoria.registrar(accion, ENTIDAD, usuario_id=usuario.id, entidad_id=categoria.id)
    db.session.commit()
    return categoria.activa
