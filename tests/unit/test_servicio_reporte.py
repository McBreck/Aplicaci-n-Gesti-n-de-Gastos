"""ReporteService: período, agrupación, totales y PDF (RF-19, RF-20; CU-13, CU-14)."""
from datetime import date, datetime
from decimal import Decimal

import pytest
from werkzeug.datastructures import MultiDict

from app.services import reporte as reporte_service
from app.services.formato import ZONA_LIMA
from app.services.reporte import SolicitudReporte
from tests.datos_verificacion import GASTOS_OCTUBRE_2026
from tests.utilidades_pdf import texto_pdf

HOY = date(2026, 10, 26)
EMITIDO = datetime(2026, 10, 26, 14, 5, tzinfo=ZONA_LIMA)
OCTUBRE = SolicitudReporte("mensual", date(2026, 10, 1), date(2026, 10, 31), "categoria")


def _solicitud(**argumentos):
    return reporte_service.interpretar_solicitud(MultiDict(argumentos), HOY)


# --- Período y agrupación --------------------------------------------------------------------

def test_por_defecto_mes_actual_por_categoria():
    solicitud, avisos, errores = _solicitud()
    assert (solicitud.tipo, solicitud.desde, solicitud.hasta, solicitud.agrupacion) == (
        "mensual", date(2026, 10, 1), date(2026, 10, 31), "categoria")
    assert (avisos, errores) == ([], [])


@pytest.mark.parametrize(
    ("argumentos", "desde", "hasta", "titulo"),
    [
        ({"tipo": "diario", "fecha": "2026-10-05"}, date(2026, 10, 5), date(2026, 10, 5), "05/10/2026"),
        ({"tipo": "semanal", "fecha": "2026-10-28"}, date(2026, 10, 26), date(2026, 11, 1),
         "Semana del 26/10/2026 al 01/11/2026"),
        ({"tipo": "mensual", "mes": "2026-02"}, date(2026, 2, 1), date(2026, 2, 28), "Febrero 2026"),
        ({"tipo": "personalizado", "desde": "2026-10-01", "hasta": "2026-10-15"}, date(2026, 10, 1),
         date(2026, 10, 15), "Del 01/10/2026 al 15/10/2026"),
    ],
)
def test_tipos_de_periodo(argumentos, desde, hasta, titulo):
    solicitud, _, _ = _solicitud(**argumentos)
    assert (solicitud.desde, solicitud.hasta, solicitud.titulo_periodo) == (desde, hasta, titulo)
    # La URL de la solicitud reproduce el mismo período (pantalla → PDF)
    reconstruida, _, _ = reporte_service.interpretar_solicitud(MultiDict(solicitud.como_argumentos()), HOY)
    assert reconstruida == solicitud


def test_personalizado_invertido_y_sin_fechas():
    solicitud, avisos, _ = _solicitud(tipo="personalizado", desde="2026-10-20", hasta="2026-10-05")
    assert (solicitud.desde, solicitud.hasta) == (date(2026, 10, 5), date(2026, 10, 20))
    assert "Intercambiamos las fechas" in avisos[0]
    solicitud, _, errores = _solicitud(tipo="personalizado", desde="2026-10-20")
    assert solicitud is None
    assert errores == ["Elige la fecha de inicio y la fecha de fin del período personalizado."]


def test_valores_desconocidos_usan_los_de_por_defecto():
    solicitud, _, _ = _solicitud(tipo="anual", agrupacion="proveedor", fecha="ayer")
    assert (solicitud.tipo, solicitud.agrupacion) == ("mensual", "categoria")
    diario, _, _ = _solicitud(tipo="diario", fecha="no-es-fecha")
    assert diario.desde == HOY


def test_nombre_del_archivo_pdf():
    reporte = reporte_service.Reporte("X", OCTUBRE, (), 0, Decimal("0.00"), EMITIDO)
    assert reporte.nombre_archivo == "reporte_gastos_20261001_20261031.pdf"


# --- Generación con los datos de verificación --------------------------------------------------

@pytest.fixture
def ana(crear_microemprendedor, cargar_gastos):
    usuario = crear_microemprendedor(nombre_negocio="PRUEBA Panadería Rosa")
    cargar_gastos(usuario, GASTOS_OCTUBRE_2026)
    return usuario


def test_reporte_por_categoria(ana):
    reporte = reporte_service.generar(ana, OCTUBRE, EMITIDO)
    assert reporte.negocio == "PRUEBA Panadería Rosa"
    assert reporte.total == Decimal("1866.80") and reporte.cantidad == 12
    assert sum(fila.total for fila in reporte.filas) == reporte.total  # RF-19: total = suma de subtotales
    assert sum(fila.cantidad for fila in reporte.filas) == 12
    primera = reporte.filas[0]
    assert (primera.grupo, primera.color, primera.cantidad, primera.total, primera.porcentaje) == (
        "Alquiler", "#93C5FD", 1, Decimal("900.00"), 48.2)
    assert [fila.grupo for fila in reporte.filas if fila.grupo == "Sin categoría"] == ["Sin categoría"]


def test_reporte_por_metodo_y_por_fecha(ana):
    por_metodo = reporte_service.generar(ana, SolicitudReporte("mensual", OCTUBRE.desde, OCTUBRE.hasta, "metodo"))
    assert [(f.grupo, f.total) for f in por_metodo.filas][:2] == [
        ("Transferencia bancaria", Decimal("1112.30")), ("Sin registrar", Decimal("338.00"))]
    assert all(fila.color is None for fila in por_metodo.filas)

    por_fecha = reporte_service.generar(ana, SolicitudReporte("mensual", OCTUBRE.desde, OCTUBRE.hasta, "fecha"))
    assert len(por_fecha.filas) == 9  # solo los días con gastos, del más antiguo al más reciente
    assert (por_fecha.filas[0].grupo, por_fecha.filas[0].cantidad, por_fecha.filas[0].total) == (
        "jue 01/10/2026", 2, Decimal("214.00"))
    assert sum(fila.total for fila in por_fecha.filas) == Decimal("1866.80")


def test_periodo_sin_gastos(ana):
    solicitud = SolicitudReporte("diario", date(2026, 10, 20), date(2026, 10, 20), "categoria")
    reporte = reporte_service.generar(ana, solicitud)
    assert reporte.vacio and reporte.filas == () and reporte.total == Decimal("0.00")


def test_negocio_por_defecto_es_el_nombre(crear_microemprendedor):
    usuario = crear_microemprendedor("prueba.sin.negocio@ejemplo.com", nombre="PRUEBA Luis Ramos")
    assert reporte_service.generar(usuario, OCTUBRE).negocio == "PRUEBA Luis Ramos"


# --- PDF ------------------------------------------------------------------------------------------

def test_pdf_con_los_mismos_datos_que_la_pantalla(ana):
    reporte = reporte_service.generar(ana, OCTUBRE, EMITIDO)
    contenido = reporte_service.generar_pdf(reporte)
    assert contenido.startswith(b"%PDF")
    texto = texto_pdf(contenido)
    for esperado in ("PRUEBA Panadería Rosa", "Reporte de gastos", "Octubre 2026", "Fecha de emisión:",
                     "26/10/2026 14:05", "Generado por ControlGastos", "Página 1", "Total del período:",
                     "S/ 1,866.80", "12 gastos"):
        assert esperado in texto, esperado
    for fila in reporte.filas:
        assert fila.grupo in texto and f"S/ {fila.total:,.2f}" in texto


def test_pdf_de_un_periodo_sin_gastos(ana):
    vacio = reporte_service.generar(ana, SolicitudReporte("diario", date(2026, 10, 20), date(2026, 10, 20), "metodo"))
    texto = texto_pdf(reporte_service.generar_pdf(vacio))
    assert "No hay gastos registrados en este período." in texto


def test_pdf_escapa_el_texto_del_usuario(crear_microemprendedor):
    usuario = crear_microemprendedor("prueba.amp@ejemplo.com", nombre_negocio="PRUEBA Pan & Café <Norte>")
    texto = texto_pdf(reporte_service.generar_pdf(reporte_service.generar(usuario, OCTUBRE)))
    assert "PRUEBA Pan & Café <Norte>" in texto
