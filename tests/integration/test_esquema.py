"""La migración inicial crea el esquema de EDT 2.2 y sus restricciones rechazan datos inválidos."""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import DataError, IntegrityError

from app.extensions import db
from app.models import Categoria, Gasto, MetodoPago, Presupuesto, Usuario

TABLAS = {"usuario", "categoria", "metodo_pago", "gasto", "presupuesto", "auditoria"}

METODOS_ESPERADOS = [
    (1, "Efectivo"),
    (2, "Yape"),
    (3, "Plin"),
    (4, "Transferencia bancaria"),
    (5, "Tarjeta"),
]

PLANTILLA_ESPERADA = [
    ("Insumos y materia prima", "#8B7BFF"),
    ("Mercadería", "#FFD166"),
    ("Servicios (luz, agua, gas)", "#7EF0C0"),
    ("Alquiler", "#93C5FD"),
    ("Transporte", "#F9A8D4"),
    ("Sueldos y pagos a terceros", "#FDBA74"),
    ("Mantenimiento", "#BEF264"),
    ("Empaques y envases", "#67E8F9"),
    ("Otros", "#CBD5E1"),
]


def _rechaza(sesion, objeto, error=IntegrityError):
    sesion.add(objeto)
    with pytest.raises(error):
        sesion.flush()
    sesion.rollback()


# --- Estructura y catálogos ---------------------------------------------------

def test_migracion_crea_las_seis_tablas(app):
    tablas = set(inspect(db.engine).get_table_names()) - {"alembic_version"}
    assert tablas == TABLAS


def test_migracion_carga_los_cinco_metodos_de_pago(sesion):
    metodos = sesion.execute(select(MetodoPago.id, MetodoPago.nombre).order_by(MetodoPago.id)).all()
    assert [tuple(fila) for fila in metodos] == METODOS_ESPERADOS


def test_migracion_carga_las_nueve_categorias_plantilla(sesion):
    consulta = (
        select(Categoria.nombre, Categoria.color)
        .where(Categoria.usuario_id.is_(None))
        .order_by(Categoria.id)
    )
    assert [tuple(fila) for fila in sesion.execute(consulta)] == PLANTILLA_ESPERADA


def test_indices_parciales_de_gasto(app):
    indices = {i["name"]: i for i in inspect(db.engine).get_indexes("gasto")}
    assert {"ix_gasto_usuario_fecha", "ix_gasto_usuario_categoria"} <= set(indices)
    for nombre in ("ix_gasto_usuario_fecha", "ix_gasto_usuario_categoria"):
        assert "eliminado = false" in indices[nombre]["dialect_options"]["postgresql_where"]


# --- CHECK ----------------------------------------------------------------------

@pytest.mark.parametrize("monto", [Decimal("0"), Decimal("-5.00")])
def test_check_monto_de_gasto_mayor_que_cero(sesion, crear_usuario, monto):
    usuario = crear_usuario()
    _rechaza(sesion, Gasto(usuario_id=usuario.id, fecha=date(2026, 10, 1), monto=monto))


def test_monto_de_gasto_admite_hasta_99999999_99(sesion, crear_usuario):
    usuario = crear_usuario()
    sesion.add(Gasto(usuario_id=usuario.id, fecha=date(2026, 10, 1), monto=Decimal("99999999.99")))
    sesion.commit()
    _rechaza(
        sesion,
        Gasto(usuario_id=usuario.id, fecha=date(2026, 10, 1), monto=Decimal("100000000.00")),
        error=DataError,
    )


@pytest.mark.parametrize(
    "campos",
    [
        {"anio": 2025, "mes": 10, "monto": Decimal("100")},
        {"anio": 2101, "mes": 10, "monto": Decimal("100")},
        {"anio": 2026, "mes": 0, "monto": Decimal("100")},
        {"anio": 2026, "mes": 13, "monto": Decimal("100")},
        {"anio": 2026, "mes": 10, "monto": Decimal("-1")},
    ],
)
def test_check_de_presupuesto(sesion, crear_usuario, campos):
    usuario = crear_usuario()
    _rechaza(sesion, Presupuesto(usuario_id=usuario.id, categoria_id=1, **campos))


def test_presupuesto_admite_monto_cero(sesion, crear_usuario):
    usuario = crear_usuario()
    sesion.add(Presupuesto(usuario_id=usuario.id, categoria_id=1, anio=2026, mes=10, monto=0))
    sesion.commit()


def test_check_rol_de_usuario(sesion):
    _rechaza(sesion, Usuario(nombre="PRUEBA X", correo="x@ejemplo.com", password_hash="h", rol="invitado"))


def test_gasto_exige_fecha_y_monto(sesion, crear_usuario):
    usuario = crear_usuario()
    _rechaza(sesion, Gasto(usuario_id=usuario.id, monto=Decimal("10")))
    _rechaza(sesion, Gasto(usuario_id=usuario.id, fecha=date(2026, 10, 1)))


# --- UNIQUE ---------------------------------------------------------------------

def test_unique_correo(sesion, crear_usuario):
    crear_usuario("repetido@ejemplo.com")
    _rechaza(sesion, Usuario(nombre="PRUEBA B", correo="repetido@ejemplo.com", password_hash="h"))


def test_unique_presupuesto_por_categoria_mes_y_anio(sesion, crear_usuario):
    usuario = crear_usuario()
    sesion.add(Presupuesto(usuario_id=usuario.id, categoria_id=1, anio=2026, mes=10, monto=400))
    sesion.commit()
    _rechaza(sesion, Presupuesto(usuario_id=usuario.id, categoria_id=1, anio=2026, mes=10, monto=500))
    # Otro mes sí se permite
    sesion.add(Presupuesto(usuario_id=usuario.id, categoria_id=1, anio=2026, mes=11, monto=500))
    sesion.commit()


def test_unique_nombre_de_categoria_sin_distinguir_mayusculas(sesion, crear_usuario):
    ana = crear_usuario("ana@ejemplo.com")
    luis = crear_usuario("luis@ejemplo.com")
    sesion.add(Categoria(usuario_id=ana.id, nombre="Delivery"))
    sesion.commit()
    _rechaza(sesion, Categoria(usuario_id=ana.id, nombre="DELIVERY"))
    # El mismo nombre en otra cuenta sí se permite
    sesion.add(Categoria(usuario_id=luis.id, nombre="delivery"))
    sesion.commit()


def test_unique_nombre_en_la_plantilla(sesion):
    _rechaza(sesion, Categoria(usuario_id=None, nombre="OTROS"))


# --- Valores por defecto y completitud -------------------------------------------

def test_valores_por_defecto(sesion, crear_usuario):
    usuario = crear_usuario()
    assert usuario.rol == "microemprendedor"
    assert usuario.activo is True
    assert usuario.intentos_fallidos == 0
    assert usuario.creado_en is not None

    categoria = Categoria(usuario_id=usuario.id, nombre="Delivery")
    sesion.add(categoria)
    sesion.commit()
    assert categoria.color == "#8B7BFF"
    assert categoria.activa is True
    assert categoria.predeterminada is False


def test_es_completo_se_recalcula_al_crear_y_modificar(sesion, crear_usuario):
    usuario = crear_usuario()
    gasto = Gasto(usuario_id=usuario.id, fecha=date(2026, 10, 1), monto=Decimal("24.00"))
    sesion.add(gasto)
    sesion.commit()
    assert gasto.es_completo is False
    assert gasto.eliminado is False
    creado = gasto.actualizado_en

    gasto.categoria_id = 1
    gasto.descripcion = "Harina 1 saco"
    gasto.metodo_pago_id = 1
    sesion.commit()
    assert gasto.es_completo is True
    assert gasto.actualizado_en > creado

    gasto.descripcion = None
    sesion.commit()
    assert gasto.es_completo is False


def test_eliminar_usuario_borra_sus_datos_en_cascada(sesion, crear_usuario):
    usuario = crear_usuario()
    sesion.add(Gasto(usuario_id=usuario.id, fecha=date(2026, 10, 1), monto=Decimal("5")))
    sesion.add(Categoria(usuario_id=usuario.id, nombre="Delivery"))
    sesion.commit()
    sesion.delete(usuario)
    sesion.commit()
    assert sesion.scalar(select(Gasto).where(Gasto.usuario_id == usuario.id)) is None
    assert sesion.scalar(select(Categoria).where(Categoria.usuario_id == usuario.id)) is None
