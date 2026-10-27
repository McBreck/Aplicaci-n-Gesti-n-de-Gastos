"""CU-13 y CU-14: reporte en pantalla y PDF (CP-26, CP-27) y rendimiento orientativo (RNF-01)."""
import re
import time
from datetime import date, timedelta

import pytest

from app.services import reporte as reporte_service
from app.services.formato import hoy_lima
from tests.datos_verificacion import GASTOS_OCTUBRE_2026
from tests.utilidades_pdf import texto_pdf

OCTUBRE = "tipo=mensual&mes=2026-10"


@pytest.fixture
def ana(crear_microemprendedor, iniciar_sesion):
    usuario = crear_microemprendedor(nombre_negocio="PRUEBA Panadería Rosa")
    iniciar_sesion("prueba.ana@ejemplo.com")
    return usuario


@pytest.fixture
def octubre(ana, cargar_gastos):
    return cargar_gastos(ana, GASTOS_OCTUBRE_2026)


def _texto(respuesta) -> str:
    return respuesta.get_data(as_text=True)


# --- CP-26 Reporte en pantalla (RF-19) -------------------------------------------------------------

def test_cp26_selector_de_periodo_y_agrupacion(cliente, ana):
    texto = _texto(cliente.get("/reportes"))
    for valor in ("diario", "semanal", "mensual", "personalizado"):
        assert f'id="periodo-{valor}"' in texto
    assert re.search(r'id="periodo-mensual" value="mensual"\s+checked', texto)
    assert re.search(r'id="agrupacion-categoria" value="categoria"\s+checked', texto)
    assert f'value="{hoy_lima().strftime("%Y-%m")}" selected' in texto
    assert "Generar reporte" in texto and "Descargar PDF" not in texto


def test_cp26_reporte_mensual_por_categoria(cliente, octubre):
    texto = _texto(cliente.get(f"/reportes/generar?{OCTUBRE}&agrupacion=categoria"))
    assert "PRUEBA Panadería Rosa" in texto and "Reporte de gastos" in texto
    assert "Octubre 2026 · Agrupado por categoría" in texto
    assert "Fecha de emisión" in texto
    total = re.search(r'<tr class="cg-fila-total">.*?</tr>', texto, re.S).group(0)
    assert "S/ 1,866.80" in total and ">12<" in total  # RF-19: total = suma del período
    # En celulares la cantidad se lee bajo el grupo (la columna se oculta para no desbordar)
    assert ">12 gastos<" in total and ">1 gasto<" in texto
    assert texto.count('data-cg-color="') >= 6  # punto de color por categoría
    assert 'href="/reportes/pdf?tipo=mensual&amp;agrupacion=categoria&amp;mes=2026-10"' in texto


@pytest.mark.parametrize(
    ("consulta", "total", "fragmento"),
    [
        (f"{OCTUBRE}&agrupacion=metodo", "S/ 1,866.80", "Transferencia bancaria"),
        (f"{OCTUBRE}&agrupacion=fecha", "S/ 1,866.80", "jue 01/10/2026"),
        ("tipo=diario&fecha=2026-10-05&agrupacion=categoria", "S/ 92.50", "05/10/2026"),
        ("tipo=semanal&fecha=2026-10-07&agrupacion=categoria", "S/ 679.80", "Semana del 05/10/2026 al 11/10/2026"),
        ("tipo=personalizado&desde=2026-10-05&hasta=2026-10-08&agrupacion=metodo", "S/ 399.80",
         "Del 05/10/2026 al 08/10/2026"),
    ],
)
def test_cp26_tipos_y_agrupaciones(cliente, octubre, consulta, total, fragmento):
    texto = _texto(cliente.get(f"/reportes/generar?{consulta}"))
    fila_total = re.search(r'<tr class="cg-fila-total">.*?</tr>', texto, re.S).group(0)
    assert total in fila_total
    assert fragmento in texto


def test_cp26_periodo_sin_gastos(cliente, octubre):
    texto = _texto(cliente.get("/reportes/generar?tipo=diario&fecha=2026-10-20"))
    assert "No hay gastos registrados en este período" in texto  # CU-13, flujo alterno 4a
    assert "Descargar PDF" not in texto


def test_cp26_personalizado_sin_fechas(cliente, ana):
    texto = _texto(cliente.get("/reportes/generar?tipo=personalizado&desde=2026-10-01"))
    assert "Elige la fecha de inicio y la fecha de fin del período personalizado." in texto
    assert re.search(r'id="periodo-personalizado" value="personalizado"\s+checked', texto)
    assert 'value="2026-10-01"' in texto


def test_cp26_mismos_valores_que_el_dashboard(cliente, octubre):
    # RF-15: el dashboard muestra los mismos valores que el reporte del mismo período
    dashboard = _texto(cliente.get("/?mes=2026-10"))
    reporte = _texto(cliente.get(f"/reportes/generar?{OCTUBRE}"))
    assert "S/ 1,866.80" in dashboard and "S/ 1,866.80" in reporte


def test_cp26_solo_datos_del_usuario(cliente, octubre, crear_microemprendedor, cargar_gastos):
    luis = crear_microemprendedor("prueba.luis@ejemplo.com")
    cargar_gastos(luis, [("2026-10-03", "999.00", "Alquiler", "Ajeno", "Efectivo")])
    texto = _texto(cliente.get(f"/reportes/generar?{OCTUBRE}"))
    assert "S/ 999.00" not in texto and "S/ 1,866.80" in texto


# --- CP-27 Exportar a PDF (RF-20) --------------------------------------------------------------------

def test_cp27_descarga_del_pdf(cliente, octubre):
    respuesta = cliente.get(f"/reportes/pdf?{OCTUBRE}&agrupacion=categoria")
    assert respuesta.status_code == 200
    assert respuesta.mimetype == "application/pdf"
    assert respuesta.headers["Content-Disposition"] == 'attachment; filename="reporte_gastos_20261001_20261031.pdf"'
    assert respuesta.headers["Cache-Control"] == "no-store"
    texto = texto_pdf(respuesta.data)
    for esperado in ("PRUEBA Panadería Rosa", "Reporte de gastos", "Octubre 2026", "Fecha de emisión:",
                     "S/ 1,866.80", "S/ 900.00", "Alquiler", "Sin categoría", "Generado por ControlGastos"):
        assert esperado in texto, esperado


def test_cp27_error_al_generar_el_pdf(cliente, octubre, monkeypatch):
    def fallar(_reporte):
        raise RuntimeError("falla simulada")

    monkeypatch.setattr(reporte_service, "generar_pdf", fallar)
    respuesta = cliente.get(f"/reportes/pdf?{OCTUBRE}&agrupacion=metodo")
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/reportes/generar?tipo=mensual&agrupacion=metodo&mes=2026-10"
    texto = _texto(cliente.get(respuesta.headers["Location"]))
    assert "No se pudo generar el PDF. Vuelve a intentarlo." in texto  # CU-14, flujo alterno 2a
    assert "S/ 1,866.80" in texto


def test_cp27_pdf_con_periodo_invalido(cliente, ana):
    respuesta = cliente.get("/reportes/pdf?tipo=personalizado", follow_redirects=True)
    assert "Elige la fecha de inicio y la fecha de fin" in _texto(respuesta)


# --- Acceso y rendimiento ------------------------------------------------------------------------------

@pytest.mark.parametrize("ruta", ["/reportes", "/reportes/generar", "/reportes/pdf"])
def test_administrador_no_tiene_reportes_de_gastos(cliente, crear_admin, iniciar_sesion, ruta):
    crear_admin()
    iniciar_sesion("prueba.admin@ejemplo.com")
    assert cliente.get(ruta).status_code == 403


def test_rnf01_reporte_de_500_gastos_en_menos_de_un_segundo(cliente, ana, cargar_gastos):
    """Prueba orientativa: la medición oficial (CP-28) se hace en la fase 4.0 con cronómetro."""
    categorias = ("Insumos y materia prima", "Servicios (luz, agua, gas)", "Transporte", None)
    metodos = ("Efectivo", "Yape", None)
    filas = [
        (date(2026, 10, 1) + timedelta(days=indice % 31), f"{(indice % 97) + 1}.50",
         categorias[indice % 4], f"PRUEBA gasto {indice}", metodos[indice % 3])
        for indice in range(500)
    ]
    cargar_gastos(ana, filas)
    cliente.get(f"/reportes/generar?{OCTUBRE}")  # primera carga de plantillas
    for agrupacion in ("categoria", "metodo", "fecha"):
        inicio = time.perf_counter()
        respuesta = cliente.get(f"/reportes/generar?{OCTUBRE}&agrupacion={agrupacion}")
        duracion = time.perf_counter() - inicio
        assert respuesta.status_code == 200
        assert ">500<" in _texto(respuesta)
        assert duracion < 1.0, f"{agrupacion}: {duracion:.3f} s"
