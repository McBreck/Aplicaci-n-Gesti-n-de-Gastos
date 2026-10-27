"""CU-11 y CU-12: dashboard del mes y datos de los gráficos (CP-22 a CP-25)."""
import re
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.models import Presupuesto
from app.services import analitica
from app.services import categoria as categoria_service
from app.services.formato import hoy_lima, mes_anio
from tests.datos_verificacion import GASTOS_OCTUBRE_2026, PRESUPUESTO_OCTUBRE_2026

OCTUBRE = date(2026, 10, 1)


@pytest.fixture
def ana(crear_microemprendedor, iniciar_sesion):
    usuario = crear_microemprendedor()
    iniciar_sesion("prueba.ana@ejemplo.com")
    return usuario


@pytest.fixture
def presupuestar(sesion, id_categoria):
    def _presupuestar(usuario, montos: dict, mes: date):
        for nombre, monto in montos.items():
            sesion.add(Presupuesto(usuario_id=usuario.id, categoria_id=id_categoria(usuario, nombre),
                                   anio=mes.year, mes=mes.month, monto=Decimal(monto)))
        sesion.commit()
    return _presupuestar


@pytest.fixture
def octubre(ana, cargar_gastos, presupuestar):
    cargar_gastos(ana, GASTOS_OCTUBRE_2026)
    presupuestar(ana, PRESUPUESTO_OCTUBRE_2026, OCTUBRE)


def _texto(respuesta) -> str:
    return respuesta.get_data(as_text=True)


# --- CP-22 Cuatro KPI con los mismos valores que el listado (RF-15) -----------------------------

def test_cp22_kpi_del_mes(cliente, ana, octubre):
    texto = _texto(cliente.get("/?mes=2026-10"))
    assert "Gastado en octubre" in texto
    assert "S/ 1,866.80" in texto
    assert "Sin gastos a la misma fecha de septiembre para comparar" in texto
    assert "94.5 %" in texto  # A9
    assert "66.7 %" in texto and "Dato más omitido: método de pago" in texto  # A8
    esperado = analitica.analizar_mes(ana.id, OCTUBRE, hoy_lima()).proyeccion
    assert esperado.suficiente and f"S/ {esperado.valor:,.2f}" in texto  # P1
    assert "Estimación al ritmo actual" in texto
    # Mismo total y completitud que Mis gastos para el mismo período
    listado = _texto(cliente.get("/gastos?desde=2026-10-01&hasta=2026-10-31"))
    assert "S/ 1,866.80" in listado and "66.7 %" in listado


def test_cp22_variacion_frente_al_mes_anterior(cliente, ana, cargar_gastos):
    hoy = hoy_lima()
    mes_pasado = (hoy.replace(day=1) - timedelta(days=1)).replace(day=1)
    cargar_gastos(ana, [(mes_pasado, "100.00", "Transporte", "Pasaje", "Efectivo"),
                        (hoy.replace(day=1), "150.00", "Transporte", "Pasaje", "Efectivo")])
    texto = _texto(cliente.get("/"))
    assert "50.0 % más que a la misma fecha de" in texto


def test_cp22_selector_de_mes(cliente, ana, octubre):
    texto = _texto(cliente.get("/?mes=2026-09"))
    assert "Septiembre 2026" in texto
    assert "Aún no registras gastos este mes" in texto
    futuro = _texto(cliente.get("/?mes=2100-01"))  # un mes futuro se lleva al mes en curso
    assert mes_anio(hoy_lima()) in futuro
    assert 'aria-label="Ver ' in futuro


# --- CP-23 Datos de los gráficos: solo del usuario y coherentes con el total (RF-15, RF-16) ----------

def test_cp23_api_del_dashboard(cliente, ana, octubre, crear_microemprendedor, cargar_gastos):
    luis = crear_microemprendedor("prueba.luis@ejemplo.com")
    cargar_gastos(luis, [("2026-10-06", "999.00", "Alquiler", "Ajeno", "Efectivo")])
    respuesta = cliente.get("/api/dashboard?mes=2026-10&semana=2026-10-08")
    assert respuesta.status_code == 200 and respuesta.is_json
    datos = respuesta.get_json()

    semana = datos["semana"]
    assert semana["lunes"] == "2026-10-05" and semana["titulo"] == "5 oct – 11 oct"
    assert semana["anterior"] == "2026-09-28"
    assert semana["total"] == 679.80  # S1 sin el gasto de otra cuenta
    assert semana["etiquetas"][0] == "lun 5"
    assert semana["series"][0]["categoria"] == "Servicios (luz, agua, gas)"
    assert "Ajeno" not in respuesta.get_data(as_text=True)

    acumulado = datos["acumulado"]
    assert len(acumulado["etiquetas"]) == 31
    assert acumulado["real"][8] == 1866.80  # día 9
    assert acumulado["presupuesto"] == 1930.0

    metodos = datos["metodos"]
    assert round(sum(metodos["valores"]), 2) == 1866.80  # la suma por método es el total del mes
    assert metodos["colores"][metodos["etiquetas"].index("Sin registrar")] == "#D1D5DB"
    assert set(metodos["colores"]) == {"#111827", "#D1D5DB"}


def test_cp23_semana_futura_se_lleva_a_la_actual(cliente, ana):
    hoy = hoy_lima()
    datos = cliente.get(f"/api/dashboard?semana={(hoy + timedelta(days=30)).isoformat()}").get_json()
    assert datos["semana"]["lunes"] == (hoy - timedelta(days=hoy.weekday())).isoformat()
    assert datos["semana"]["siguiente"] is None


def test_cp23_api_sin_sesion_o_de_administrador(cliente, sesion, crear_admin, iniciar_sesion):
    sin_sesion = cliente.get("/api/dashboard")
    assert sin_sesion.status_code == 401 and "Vuelve a iniciar sesión" in sin_sesion.get_json()["error"]
    crear_admin()
    iniciar_sesion("prueba.admin@ejemplo.com")
    respuesta = cliente.get("/api/dashboard")
    assert respuesta.status_code == 403 and respuesta.is_json


def test_cp23_graficos_y_chartjs_solo_en_el_dashboard(cliente, ana, octubre):
    texto = _texto(cliente.get("/?mes=2026-10"))
    assert 'data-cg-api="/api/dashboard?mes=2026-10"' in texto
    for lienzo in ("grafico-semana", "grafico-acumulado", "grafico-metodos"):
        assert f'id="{lienzo}"' in texto
    assert "/static/vendor/chartjs-4.4.9/chart.umd.js" in texto
    assert "chart.umd.js" not in _texto(cliente.get("/gastos"))  # RNF-02


# --- CP-24 Proyección y recomendaciones (CU-12, RF-17, RF-18) ---------------------------------------

def test_cp24_recomendaciones_con_accion(cliente, ana, octubre):
    texto = _texto(cliente.get("/?mes=2026-10"))
    assert "Servicios (luz, agua, gas) superó su presupuesto en S/ 30.30 (5.8 %)." in texto
    assert "Ver gastos de la categoría" in texto
    assert texto.count('class="cg-recomendacion"') <= 3  # RN-08


def test_cp24_datos_insuficientes_y_gastos_bajo_control(cliente, ana, cargar_gastos, presupuestar):
    hoy = hoy_lima()
    presupuestar(ana, {"Transporte": "100.00"}, hoy.replace(day=1))
    cargar_gastos(ana, [(hoy, "10.00", "Transporte", "Pasaje", "Efectivo")])
    texto = _texto(cliente.get("/"))
    assert "Datos insuficientes para proyectar" in texto  # flujo alterno de CU-12
    assert "Tus gastos están bajo control este mes" in texto


# --- CP-25 Estados especiales, tarjetas rápidas y actividad (CU-11, RNF-05) ----------------------------

def test_cp25_mes_sin_gastos(cliente, ana):
    texto = _texto(cliente.get("/"))
    assert "Aún no registras gastos este mes" in texto
    assert "S/ 0.00" in texto
    assert "Define tu presupuesto para ver si te mantienes dentro de lo planificado" in texto
    assert "grafico-semana" not in texto and "chart.umd.js" not in texto


def test_cp25_sin_presupuesto_y_error_de_graficos(cliente, ana, cargar_gastos):
    cargar_gastos(ana, [(hoy_lima(), "12.00", "Transporte", "Pasaje", "Efectivo")])
    texto = _texto(cliente.get("/"))
    assert texto.count("Define tu presupuesto para ver si te mantienes dentro de lo planificado") == 2
    assert "Definir presupuesto" in texto
    # El aviso de error de los gráficos existe oculto; dashboard.js lo muestra si falla la carga
    assert texto.count("No se pudieron cargar los gráficos. Vuelve a intentarlo") == 3
    assert "data-cg-reintentar" in texto


def test_cp25_tarjetas_rapidas(cliente, ana, cargar_gastos, id_categoria):
    hoy = hoy_lima()
    cargar_gastos(ana, [(hoy, "5.00", "Transporte", "a", "Efectivo"), (hoy, "6.00", "Transporte", "b", "Efectivo"),
                        (hoy, "50.00", "Alquiler", "c", "Efectivo")])
    texto = _texto(cliente.get("/"))
    tarjetas = re.findall(r'<section class="cg-tarjeta cg-rapida"[^>]*aria-label="([^"]+)"', texto)
    assert tarjetas == ["Transporte", "Alquiler", "Insumos y materia prima"]  # más usadas y luego las primeras
    assert texto.count("data-cg-sumar=") == 9
    transporte = id_categoria(ana, "Transporte")
    assert f'href="/gastos/nuevo?categoria={transporte}"' in texto
    assert "S/ 11.00 este mes" in texto
    formulario = _texto(cliente.get(f"/gastos/nuevo?categoria={transporte}"))
    assert f'value="{transporte}" checked' in formulario


def test_cp25_actividad_reciente_agrupada(cliente, ana, cargar_gastos):
    hoy = hoy_lima()
    cargar_gastos(ana, [(hoy, "5.00", "Transporte", "a", "Efectivo"), (hoy, "6.00", "Transporte", "b", "Efectivo"),
                        (hoy, "7.00", "Transporte", "c", "Efectivo"), (hoy, "9.00", "Alquiler", "d", "Efectivo")])
    texto = _texto(cliente.get("/"))
    assert "3 registros" in texto
    assert re.search(r">Hoy</h3>\s*<span[^>]*>S/ 27.00<", texto)


def test_presupuesto_por_categoria_ordenado_por_porcentaje(cliente, ana, octubre):
    texto = _texto(cliente.get("/?mes=2026-10"))
    bloque = texto.split('id="titulo-presupuesto-categoria"')[1].split("</section>")[0]
    nombres = re.findall(r'cg-presupuesto-resumen__nombre">([^<]+)<', bloque)
    assert nombres == ["Servicios (luz, agua, gas)", "Alquiler", "Empaques y envases",
                       "Insumos y materia prima", "Transporte"]


def test_mas_usadas_solo_activas(ana, cargar_gastos, sesion, id_categoria):
    from app.models import Categoria

    hoy = hoy_lima()
    cargar_gastos(ana, [(hoy, "5.00", "Otros", "a", "Efectivo")])
    sesion.get(Categoria, id_categoria(ana, "Otros")).activa = False
    sesion.commit()
    nombres = [c.nombre for c in categoria_service.mas_usadas(ana.id, hoy)]
    assert nombres == ["Insumos y materia prima", "Mercadería", "Servicios (luz, agua, gas)"]
