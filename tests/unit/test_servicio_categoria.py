"""CategoriaService (RF-11): crear, renombrar, activar y desactivar categorías."""
import pytest
from sqlalchemy import select

from app.models import Auditoria, Categoria
from app.services import categoria as categoria_service
from app.services.categoria import ErrorCategoria


@pytest.fixture
def ana(crear_microemprendedor):
    return crear_microemprendedor()


def _categoria(sesion, usuario, nombre):
    return sesion.scalar(select(Categoria).where(Categoria.usuario_id == usuario.id, Categoria.nombre == nombre))


def test_crear_categoria_propia(ana, sesion):
    categoria = categoria_service.crear_categoria(ana, "  Delivery   y  envíos ", "#c4b5fd")
    assert (categoria.nombre, categoria.color, categoria.predeterminada, categoria.activa) == (
        "Delivery y envíos", "#C4B5FD", False, True)
    evento = sesion.scalar(select(Auditoria).where(Auditoria.entidad == "categoria"))
    assert (evento.accion, evento.entidad_id) == ("CREAR", categoria.id)


@pytest.mark.parametrize(
    ("nombre", "color", "mensaje"),
    [
        ("OTROS", "#8B7BFF", "Ya tienes una categoría con ese nombre"),
        ("insumos y materia prima", "#8B7BFF", "Ya tienes una categoría con ese nombre"),
        ("   ", "#8B7BFF", "Escribe el nombre de la categoría."),
        ("x" * 61, "#8B7BFF", "hasta 60 caracteres"),
        ("Delivery", "#000000", "Elige uno de los colores de la paleta."),
        ("Delivery", "", "Elige uno de los colores de la paleta."),
    ],
)
def test_crear_rechaza_datos_invalidos(ana, nombre, color, mensaje):
    with pytest.raises(ErrorCategoria, match=mensaje):
        categoria_service.crear_categoria(ana, nombre, color)


def test_el_mismo_nombre_en_otra_cuenta_esta_permitido(ana, crear_microemprendedor):
    luis = crear_microemprendedor("prueba.luis@ejemplo.com")
    categoria_service.crear_categoria(ana, "Delivery", "#8B7BFF")
    assert categoria_service.crear_categoria(luis, "delivery", "#8B7BFF").nombre == "delivery"


def test_renombrar_solo_las_propias(ana, sesion):
    propia = categoria_service.crear_categoria(ana, "Delivery", "#8B7BFF")
    categoria_service.renombrar_categoria(propia, ana, "Envíos")
    assert propia.nombre == "Envíos"
    evento = sesion.scalar(select(Auditoria).where(Auditoria.accion == "MODIFICAR"))
    assert evento.detalle == {"anterior": {"nombre": "Delivery"}, "nuevo": {"nombre": "Envíos"}}

    with pytest.raises(ErrorCategoria, match="predeterminadas no se pueden renombrar"):
        categoria_service.renombrar_categoria(_categoria(sesion, ana, "Otros"), ana, "Varios")
    with pytest.raises(ErrorCategoria, match="Ya tienes una categoría con ese nombre"):
        categoria_service.renombrar_categoria(propia, ana, "ALQUILER")


def test_renombrar_con_el_mismo_nombre_no_audita(ana, sesion):
    propia = categoria_service.crear_categoria(ana, "Delivery", "#8B7BFF")
    categoria_service.renombrar_categoria(propia, ana, "Delivery")
    assert sesion.scalar(select(Auditoria).where(Auditoria.accion == "MODIFICAR")) is None
    # Cambiar solo mayúsculas sí se permite (es la misma categoría)
    categoria_service.renombrar_categoria(propia, ana, "DELIVERY")
    assert propia.nombre == "DELIVERY"


def test_activar_y_desactivar_cualquier_categoria(ana, sesion):
    otros = _categoria(sesion, ana, "Otros")
    assert categoria_service.cambiar_estado(otros, ana) is False
    assert categoria_service.cambiar_estado(otros, ana) is True
    acciones = [e.accion for e in sesion.scalars(select(Auditoria).order_by(Auditoria.id))]
    assert acciones == ["DESACTIVAR", "ACTIVAR"]


def test_listar_solo_activas_o_incluyendo_una_inactiva(ana, sesion):
    otros = _categoria(sesion, ana, "Otros")
    categoria_service.cambiar_estado(otros, ana)
    activas = categoria_service.listar_categorias(ana.id)
    assert len(activas) == 8 and otros not in activas
    assert otros in categoria_service.listar_categorias(ana.id, incluir_id=otros.id)
    assert len(categoria_service.listar_categorias(ana.id, solo_activas=False)) == 9
