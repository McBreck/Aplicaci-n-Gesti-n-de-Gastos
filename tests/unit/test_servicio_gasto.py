"""GastoService: validación (RN-02 a RN-04), filtros, completitud A8 y agrupación por fecha."""
from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from werkzeug.datastructures import MultiDict

from app.models import Auditoria, Categoria, Gasto
from app.services import gasto as gasto_service
from app.services.gasto import FiltrosGastos, ResumenGastos
from app.services.formato import hoy_lima
from tests.datos_verificacion import (
    CAMPO_MAS_OMITIDO_OCTUBRE_2026,
    COMPLETITUD_OCTUBRE_2026,
    GASTOS_OCTUBRE_2026,
    TOTAL_OCTUBRE_2026,
)

HOY = date(2026, 10, 26)
OCTUBRE = FiltrosGastos(desde=date(2026, 10, 1), hasta=date(2026, 10, 31))


# --- Monto (RN-03) -------------------------------------------------------------------

@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("15.50", "15.50"), ("15,50", "15.50"), ("15,5", "15.50"), ("1,234.56", "1234.56"),
        ("1,234", "1234.00"), ("S/ 20", "20.00"), (" 7 ", "7.00"), ("0.01", "0.01"),
        ("99999999.99", "99999999.99"), ("15.", "15.00"), (".5", "0.50"), ("15.500", "15.50"),
    ],
)
def test_monto_valido(texto, esperado):
    assert gasto_service.interpretar_monto(texto) == Decimal(esperado)


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("", "Escribe el monto del gasto."),
        ("   ", "Escribe el monto del gasto."),
        (None, "Escribe el monto del gasto."),
        ("abc", "solo con números"),
        ("1e3", "solo con números"),
        ("NaN", "solo con números"),
        ("1.234,56", "solo con números"),
        ("12.345", "hasta dos decimales"),
        ("0", "mayor que cero"),
        ("0.00", "mayor que cero"),
        ("-5", "mayor que cero"),
        ("100000000", "no puede ser mayor que S/ 99,999,999.99"),
    ],
)
def test_monto_invalido(texto, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        gasto_service.interpretar_monto(texto)


# --- Fecha (RN-04) ---------------------------------------------------------------------

def test_fecha_valida_en_ambos_formatos():
    assert gasto_service.interpretar_fecha("2026-10-26", HOY) == HOY
    assert gasto_service.interpretar_fecha("01/10/2026", HOY) == date(2026, 10, 1)


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [
        ("2026-10-27", "La fecha no puede ser posterior a hoy."),
        ("", "Elige la fecha del gasto."),
        ("31/02/2026", "Escribe una fecha válida"),
        ("ayer", "Escribe una fecha válida"),
    ],
)
def test_fecha_invalida(texto, mensaje):
    with pytest.raises(ValueError, match=mensaje):
        gasto_service.interpretar_fecha(texto, HOY)


# --- Filtros (RF-09) ---------------------------------------------------------------------

def test_filtros_por_defecto_mes_actual():
    filtros, avisos = gasto_service.interpretar_filtros(MultiDict(), HOY)
    assert filtros == FiltrosGastos(desde=date(2026, 10, 1), hasta=HOY)
    assert avisos == []


def test_fechas_vacias_significan_sin_limite():
    filtros, _ = gasto_service.interpretar_filtros(MultiDict({"desde": "", "hasta": ""}), HOY)
    assert filtros.desde is None and filtros.hasta is None


def test_fechas_invertidas_se_intercambian():
    filtros, avisos = gasto_service.interpretar_filtros(MultiDict({"desde": "2026-10-20", "hasta": "2026-10-05"}), HOY)
    assert (filtros.desde, filtros.hasta) == (date(2026, 10, 5), date(2026, 10, 20))
    assert "Intercambiamos las fechas" in avisos[0]


def test_valores_invalidos_se_ignoran():
    argumentos = MultiDict({"desde": "xx", "categoria": "abc", "metodo": "sin", "estado": "raro", "q": "  harina  "})
    filtros, avisos = gasto_service.interpretar_filtros(argumentos, HOY)
    assert filtros.desde is None
    assert "no es válida" in avisos[0]
    assert (filtros.categoria, filtros.metodo, filtros.estado, filtros.q) == ("", "sin", "", "harina")
    assert filtros.cantidad_adicionales() == 2


def test_busqueda_limitada_a_100_caracteres():
    filtros, _ = gasto_service.interpretar_filtros(MultiDict({"q": "a" * 150}), HOY)
    assert len(filtros.q) == 100


def test_filtros_se_reproducen_desde_la_url():
    original = FiltrosGastos(desde=None, hasta=HOY, categoria="7", metodo="sin", estado="incompleto", q="gas")
    reconstruido, _ = gasto_service.interpretar_filtros(MultiDict(original.como_argumentos()), HOY)
    assert reconstruido == original


# --- Completitud A8 (RF-10) ------------------------------------------------------------------

def test_resumen_de_completitud():
    resumen = ResumenGastos(
        cantidad=12, total=Decimal("1866.80"), completos=8,
        faltantes={"categoría": 1, "descripción": 1, "método de pago": 2},
    )
    assert resumen.porcentaje_completitud == 66.7
    assert resumen.campo_mas_omitido == "método de pago"
    assert resumen.incompletos == 4


def test_campo_mas_omitido_desempata_en_el_orden_de_rn01():
    resumen = ResumenGastos(cantidad=4, completos=2, faltantes={"categoría": 2, "descripción": 2, "método de pago": 0})
    assert resumen.campo_mas_omitido == "categoría"


def test_resumen_sin_registros_o_todo_completo():
    assert ResumenGastos().porcentaje_completitud is None
    assert ResumenGastos().campo_mas_omitido is None
    completo = ResumenGastos(cantidad=3, completos=3, faltantes={"categoría": 0})
    assert completo.porcentaje_completitud == 100.0
    assert completo.campo_mas_omitido is None


# --- Agrupación por fecha (componente actividad) ---------------------------------------------

def _gasto(id_, fecha, monto, categoria_id):
    categoria = SimpleNamespace(nombre=f"C{categoria_id}", color="#8B7BFF") if categoria_id else None
    return SimpleNamespace(id=id_, fecha=fecha, monto=Decimal(monto), categoria_id=categoria_id, categoria=categoria)


def _gastos_de_ejemplo():
    ayer = HOY - timedelta(days=1)
    return [
        _gasto(1, HOY, "10", 1), _gasto(2, HOY, "5", 1), _gasto(3, HOY, "7", 2),
        _gasto(4, ayer, "3", None),
        _gasto(5, date(2026, 10, 21), "8", 2),
    ]


def test_agrupa_por_fecha_con_etiquetas_y_totales():
    dias = gasto_service.agrupar_actividad(_gastos_de_ejemplo(), HOY)
    assert [dia.etiqueta for dia in dias] == ["Hoy", "Ayer", "mié, 21 oct"]
    assert [dia.total for dia in dias] == [Decimal("22"), Decimal("3"), Decimal("8")]
    assert [len(dia.filas) for dia in dias] == [3, 1, 1]
    assert not any(fila.es_grupo for dia in dias for fila in dia.filas)


def test_agrupa_gastos_de_la_misma_categoria_el_mismo_dia():
    hoy, _, _ = gasto_service.agrupar_actividad(_gastos_de_ejemplo(), HOY, agrupar_categorias=True)
    grupo, suelto = hoy.filas
    assert grupo.es_grupo and len(grupo.gastos) == 2 and grupo.total == Decimal("15")
    assert grupo.categoria.nombre == "C1"
    assert not suelto.es_grupo and suelto.gasto.id == 3
    assert grupo.clave != suelto.clave


def test_usa_el_total_del_dia_completo_si_se_indica():
    dias = gasto_service.agrupar_actividad(_gastos_de_ejemplo(), HOY, {HOY: Decimal("99.00")})
    assert dias[0].total == Decimal("99.00")


# --- Registro, modificación y eliminación (con base de datos) --------------------------------

DATOS_COMPLETOS = {"monto": "190", "fecha": "2026-10-01", "descripcion": "Harina 2 sacos", "metodo_pago_id": "1"}


@pytest.fixture
def ana(crear_microemprendedor):
    return crear_microemprendedor()


def test_registrar_gasto_completo(ana, sesion, id_categoria):
    datos = {**DATOS_COMPLETOS, "categoria_id": str(id_categoria(ana, "Insumos y materia prima"))}
    gasto = gasto_service.registrar_gasto(ana, datos)
    assert gasto.es_completo is True
    assert gasto.monto == Decimal("190.00")
    evento = sesion.scalar(select(Auditoria).where(Auditoria.accion == "CREAR", Auditoria.entidad == "gasto"))
    assert evento.entidad_id == gasto.id
    assert evento.detalle["nuevo"]["monto"] == "190.00"


def test_registrar_con_solo_fecha_y_monto(ana):
    gasto = gasto_service.registrar_gasto(ana, {"monto": "24", "fecha": "2026-10-01", "descripcion": "   "})
    assert gasto.es_completo is False
    assert gasto.descripcion is None
    assert gasto.campos_faltantes() == ["categoría", "descripción", "método de pago"]


def test_validacion_reune_todos_los_errores(ana, crear_microemprendedor, id_categoria):
    luis = crear_microemprendedor("prueba.luis@ejemplo.com")
    datos = {
        "monto": "", "fecha": (hoy_lima() + timedelta(days=1)).isoformat(),
        "categoria_id": str(id_categoria(luis, "Alquiler")), "metodo_pago_id": "99", "descripcion": "x" * 256,
    }
    with pytest.raises(gasto_service.ErrorValidacion) as error:
        gasto_service.registrar_gasto(ana, datos)
    assert set(error.value.errores) == {"monto", "fecha", "categoria_id", "metodo_pago_id", "descripcion"}
    assert error.value.errores["categoria_id"] == "Elige una de tus categorías."


def test_categoria_inactiva_solo_si_el_gasto_ya_la_tenia(ana, sesion, id_categoria):
    id_otros = id_categoria(ana, "Otros")
    sesion.get(Categoria, id_otros).activa = False
    sesion.commit()
    datos = {"monto": "10", "fecha": "2026-10-01", "categoria_id": str(id_otros)}
    with pytest.raises(gasto_service.ErrorValidacion):
        gasto_service.validar_datos(ana.id, datos)
    assert gasto_service.validar_datos(ana.id, datos, categoria_actual_id=id_otros)["categoria_id"] == id_otros


def test_modificar_completa_el_gasto_y_audita_solo_cambios(ana, sesion, id_categoria):
    gasto = gasto_service.registrar_gasto(ana, {"monto": "24", "fecha": "2026-10-01"})
    datos = {**DATOS_COMPLETOS, "monto": "24", "categoria_id": str(id_categoria(ana, "Insumos y materia prima"))}
    gasto_service.modificar_gasto(gasto, ana, datos)
    assert gasto.es_completo is True

    evento = sesion.scalar(select(Auditoria).where(Auditoria.accion == "MODIFICAR"))
    assert set(evento.detalle["nuevo"]) == {"categoria_id", "descripcion", "metodo_pago_id"}
    assert evento.detalle["anterior"]["descripcion"] is None

    gasto_service.modificar_gasto(gasto, ana, datos)  # sin cambios: no se audita de nuevo
    assert len(sesion.scalars(select(Auditoria).where(Auditoria.accion == "MODIFICAR")).all()) == 1


def test_eliminar_es_logico(ana, sesion):
    gasto = gasto_service.registrar_gasto(ana, {"monto": "24", "fecha": "2026-10-01"})
    gasto_service.eliminar_gasto(gasto, ana)
    assert sesion.get(Gasto, gasto.id).eliminado is True
    assert gasto_service.obtener_gasto_propio(ana.id, gasto.id) is None
    evento = sesion.scalar(select(Auditoria).where(Auditoria.accion == "ELIMINAR"))
    assert evento.detalle["anterior"]["monto"] == "24.00"


# --- Consulta y completitud con los datos de verificación (sección 9) --------------------------

@pytest.fixture
def octubre(ana, cargar_gastos):
    return cargar_gastos(ana, GASTOS_OCTUBRE_2026)


def test_a8_con_los_datos_de_verificacion(ana, octubre):
    resumen = gasto_service.resumir(ana.id, OCTUBRE)
    assert resumen.cantidad == 12
    assert resumen.total == Decimal(TOTAL_OCTUBRE_2026)
    assert resumen.completos == 8
    assert resumen.porcentaje_completitud == COMPLETITUD_OCTUBRE_2026
    assert resumen.campo_mas_omitido == CAMPO_MAS_OMITIDO_OCTUBRE_2026
    assert resumen.faltantes == {"categoría": 1, "descripción": 1, "método de pago": 2}


@pytest.mark.parametrize(
    ("cambios", "cantidad", "total"),
    [
        ({"categoria": "Servicios (luz, agua, gas)"}, 3, "550.30"),
        ({"categoria": "sin"}, 1, "42.00"),
        ({"metodo": 2}, 3, "136.50"),  # Yape
        ({"metodo": "sin"}, 2, "338.00"),
        ({"estado": "incompleto"}, 4, "404.00"),
        ({"estado": "completo"}, 8, "1462.80"),
        ({"q": "recibo"}, 2, "492.30"),
        ({"q": "AZUCAR"}, 1, "42.00"),  # sin distinguir tildes ni mayúsculas
        ({"q": "%"}, 0, "0.00"),  # los comodines se buscan literalmente
        ({"desde": date(2026, 10, 5), "hasta": date(2026, 10, 8)}, 6, "399.80"),
    ],
)
def test_cada_filtro_reduce_el_resultado(ana, octubre, id_categoria, cambios, cantidad, total):
    cambios = dict(cambios)
    if cambios.get("categoria") not in (None, "sin"):
        cambios["categoria"] = str(id_categoria(ana, cambios["categoria"]))
    if isinstance(cambios.get("metodo"), int):
        cambios["metodo"] = str(cambios["metodo"])
    filtros = FiltrosGastos(**{"desde": OCTUBRE.desde, "hasta": OCTUBRE.hasta, **cambios})
    resumen = gasto_service.resumir(ana.id, filtros)
    assert (resumen.cantidad, resumen.total) == (cantidad, Decimal(total))
    assert len(gasto_service.listar_gastos(ana.id, filtros).gastos) == cantidad


def test_excluye_eliminados_y_gastos_de_otros(ana, octubre, crear_microemprendedor, cargar_gastos):
    luis = crear_microemprendedor("prueba.luis@ejemplo.com")
    cargar_gastos(luis, [("2026-10-02", "500.00", "Alquiler", "Ajeno", "Efectivo")])
    gasto_service.eliminar_gasto(octubre[4], ana)  # 900.00 de alquiler
    resumen = gasto_service.resumir(ana.id, OCTUBRE)
    assert resumen.cantidad == 11
    assert resumen.total == Decimal("966.80")


def test_orden_y_paginacion_de_50(ana, cargar_gastos):
    filas = [("2026-10-02", "1.00", None, None, None)] * 52 + [("2026-10-01", "2.00", None, None, None)] * 3
    cargar_gastos(ana, filas)
    primera = gasto_service.listar_gastos(ana.id, OCTUBRE, 1)
    segunda = gasto_service.listar_gastos(ana.id, OCTUBRE, 2)
    assert (len(primera.gastos), len(segunda.gastos), primera.total_paginas) == (50, 5, 2)
    assert [g.fecha for g in segunda.gastos] == [date(2026, 10, 2)] * 2 + [date(2026, 10, 1)] * 3
    ids = [g.id for g in primera.gastos]
    assert ids == sorted(ids, reverse=True)
    # El total del día cubre también los gastos que pasan a la página siguiente
    assert primera.totales_por_dia[date(2026, 10, 2)] == Decimal("52.00")
    assert gasto_service.listar_gastos(ana.id, OCTUBRE, 99).pagina == 2
