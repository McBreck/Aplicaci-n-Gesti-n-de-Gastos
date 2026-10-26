"""CU-05 a CU-08 y CU-15: registrar, modificar, eliminar y consultar gastos (CP-10 a CP-17, CP-29)."""
import re
from datetime import timedelta
from urllib.parse import quote

import pytest
from sqlalchemy import func, select

from app.models import Auditoria, Categoria, Gasto
from app.services.formato import hoy_lima
from tests.datos_verificacion import GASTOS_OCTUBRE_2026

OCTUBRE = "desde=2026-10-01&hasta=2026-10-31"


@pytest.fixture
def ana(crear_microemprendedor, iniciar_sesion):
    usuario = crear_microemprendedor()
    iniciar_sesion("prueba.ana@ejemplo.com")
    return usuario


def _texto(respuesta) -> str:
    return respuesta.get_data(as_text=True)


def _cantidad_gastos(sesion, **condiciones) -> int:
    consulta = select(func.count(Gasto.id))
    for campo, valor in condiciones.items():
        consulta = consulta.where(getattr(Gasto, campo) == valor)
    return sesion.scalar(consulta)


def _datos(**cambios):
    return {"monto": "15.00", "fecha": hoy_lima().isoformat(), "categoria_id": "", "metodo_pago_id": "",
            "descripcion": "", **cambios}


# --- CP-10 Registrar un gasto completo (RF-05, RF-06) ------------------------------------

def test_cp10_formulario_de_registro(cliente, ana):
    texto = _texto(cliente.get("/gastos/nuevo"))
    assert f'value="{hoy_lima().isoformat()}"' in texto  # fecha de hoy por defecto
    assert texto.count('name="categoria_id"') == 9  # categorías como botones
    assert texto.count('name="metodo_pago_id"') == 5  # métodos de pago como botones
    assert 'inputmode="decimal"' in texto
    assert 'data-cg-contador="descripcion-contador"' in texto
    assert 'aria-label="Registrar gasto"' not in texto  # sin FAB en el propio formulario


def test_cp10_registrar_gasto_completo(cliente, ana, sesion, id_categoria):
    datos = _datos(categoria_id=str(id_categoria(ana, "Empaques y envases")), metodo_pago_id="2",
                   descripcion="Bolsas kraft x 100", monto="15,50")
    respuesta = cliente.post("/gastos/nuevo", data=datos)
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/gastos"

    gasto = sesion.scalar(select(Gasto).where(Gasto.usuario_id == ana.id))
    assert (gasto.monto, gasto.es_completo) == (15.5, True)
    texto = _texto(cliente.get("/gastos"))
    assert "Gasto guardado · Completo" in texto
    assert "Bolsas kraft x 100" in texto
    assert sesion.scalar(select(Auditoria).where(Auditoria.accion == "CREAR", Auditoria.entidad == "gasto"))


# --- CP-11 Registrar solo con fecha y monto: Incompleto y "Completar ahora" (CU-05 7a) ----

def test_cp11_registro_incompleto_avisa_y_ofrece_completar(cliente, ana, sesion):
    respuesta = cliente.post("/gastos/nuevo", data=_datos(), follow_redirects=True)
    texto = _texto(respuesta)
    gasto = sesion.scalar(select(Gasto).where(Gasto.usuario_id == ana.id))
    assert gasto.es_completo is False
    assert "Gasto guardado · Incompleto: falta categoría, descripción y método de pago" in texto
    assert "Completar ahora" in texto
    assert f'href="/gastos/{gasto.id}/editar"' in texto
    assert "Sin descripción" in texto and "Incompleto" in texto


# --- CP-12 Monto inválido (RN-03) ------------------------------------------------------------

@pytest.mark.parametrize(
    ("monto", "mensaje"),
    [
        ("", "Escribe el monto del gasto."),
        ("0", "El monto debe ser mayor que cero."),
        ("-5", "El monto debe ser mayor que cero."),
        ("abc", "Escribe el monto solo con números"),
        ("12.345", "El monto puede tener hasta dos decimales."),
        ("100000000", "El monto no puede ser mayor que S/ 99,999,999.99."),
    ],
)
def test_cp12_monto_invalido_se_rechaza(cliente, ana, sesion, monto, mensaje):
    respuesta = cliente.post("/gastos/nuevo", data=_datos(monto=monto, descripcion="Prueba"))
    texto = _texto(respuesta)
    assert respuesta.status_code == 200
    assert mensaje in texto
    assert 'aria-invalid="true"' in texto
    assert 'value="Prueba"' in texto  # los demás datos se conservan
    assert _cantidad_gastos(sesion, usuario_id=ana.id) == 0


# --- CP-13 Fecha futura (RN-04) ----------------------------------------------------------------

def test_cp13_fecha_posterior_a_hoy_se_rechaza(cliente, ana, sesion):
    manana = (hoy_lima() + timedelta(days=1)).isoformat()
    respuesta = cliente.post("/gastos/nuevo", data=_datos(fecha=manana))
    assert "La fecha no puede ser posterior a hoy." in _texto(respuesta)
    assert _cantidad_gastos(sesion, usuario_id=ana.id) == 0


# --- CP-14 Modificar: al completar pasa a Completo (RF-07, CU-06) --------------------------------

def test_cp14_completar_un_gasto_incompleto(cliente, ana, sesion, cargar_gastos, id_categoria):
    (gasto,) = cargar_gastos(ana, [("2026-10-01", "24.00", "Insumos y materia prima", None, "Efectivo")])
    formulario = _texto(cliente.get(f"/gastos/{gasto.id}/editar"))
    assert "Editar gasto" in formulario
    assert formulario.count("Falta completar") == 1  # solo la descripción
    assert 'value="24.00"' in formulario

    datos = _datos(monto="24.00", fecha="2026-10-01", descripcion="Harina 1 saco", metodo_pago_id="1",
                   categoria_id=str(id_categoria(ana, "Insumos y materia prima")))
    respuesta = cliente.post(f"/gastos/{gasto.id}/editar", data=datos, follow_redirects=True)
    assert "Gasto guardado · Completo" in _texto(respuesta)
    assert gasto.es_completo is True
    evento = sesion.scalar(select(Auditoria).where(Auditoria.accion == "MODIFICAR", Auditoria.entidad_id == gasto.id))
    assert evento.detalle == {"anterior": {"descripcion": None}, "nuevo": {"descripcion": "Harina 1 saco"}}


def test_cp14_edicion_con_errores_no_modifica(cliente, ana, cargar_gastos):
    (gasto,) = cargar_gastos(ana, [("2026-10-01", "24.00", None, None, None)])
    respuesta = cliente.post(f"/gastos/{gasto.id}/editar", data=_datos(monto="0", fecha="2026-10-01"))
    assert "El monto debe ser mayor que cero." in _texto(respuesta)
    assert gasto.monto == 24


def test_cp14_categoria_inactiva_se_muestra_al_editar_pero_no_al_registrar(cliente, ana, sesion, cargar_gastos, id_categoria):
    (gasto,) = cargar_gastos(ana, [("2026-10-01", "5.00", "Otros", "Varios", "Efectivo")])
    sesion.get(Categoria, id_categoria(ana, "Otros")).activa = False
    sesion.commit()
    assert "Otros" not in _texto(cliente.get("/gastos/nuevo"))
    assert "Otros (inactiva)" in _texto(cliente.get(f"/gastos/{gasto.id}/editar"))
    rechazo = cliente.post("/gastos/nuevo", data=_datos(categoria_id=str(id_categoria(ana, "Otros"))))
    assert "Elige una de tus categorías." in _texto(rechazo)


# --- CP-15 Eliminar (lógico) con confirmación (RF-08, RN-09, CU-07) ---------------------------------

def test_cp15_eliminar_gasto(cliente, ana, sesion, cargar_gastos):
    gastos = cargar_gastos(ana, [("2026-10-01", "24.00", None, "Para borrar", None),
                                 ("2026-10-02", "10.00", None, "Se queda", None)])
    lista = _texto(cliente.get(f"/gastos?{OCTUBRE}"))
    assert 'data-bs-target="#modalConfirmacion"' in lista
    assert "Se eliminará el gasto del 01/10/2026 por S/ 24.00 (Para borrar)" in lista

    volver = quote(f"/gastos?{OCTUBRE}", safe="")
    respuesta = cliente.post(f"/gastos/{gastos[0].id}/eliminar?next={volver}", follow_redirects=True)
    texto = _texto(respuesta)
    assert "Gasto eliminado." in texto
    assert "Para borrar" not in texto and "Se queda" in texto
    assert sesion.get(Gasto, gastos[0].id).eliminado is True
    assert sesion.scalar(select(Auditoria).where(Auditoria.accion == "ELIMINAR", Auditoria.entidad_id == gastos[0].id))
    assert cliente.get(f"/gastos/{gastos[0].id}/editar").status_code == 404
    assert cliente.post(f"/gastos/{gastos[0].id}/eliminar").status_code == 404


# --- CP-16 Listar y filtrar (RF-09, CU-08) -------------------------------------------------------------

@pytest.fixture
def octubre(ana, cargar_gastos):
    return cargar_gastos(ana, GASTOS_OCTUBRE_2026)


@pytest.mark.parametrize(
    ("filtro", "cantidad", "total"),
    [
        ("", "12 gastos", "S/ 1,866.80"),
        ("&metodo=2", "3 gastos", "S/ 136.50"),
        ("&estado=incompleto", "4 gastos", "S/ 404.00"),
        ("&q=recibo", "2 gastos", "S/ 492.30"),
        ("&categoria=sin", "1 gasto", "S/ 42.00"),
    ],
)
def test_cp16_cada_filtro_reduce_el_listado_y_muestra_el_total(cliente, octubre, filtro, cantidad, total):
    texto = _texto(cliente.get(f"/gastos?{OCTUBRE}{filtro}"))
    assert cantidad in texto
    assert total in texto


def test_cp16_filtro_por_categoria(cliente, ana, octubre, id_categoria):
    id_servicios = id_categoria(ana, "Servicios (luz, agua, gas)")
    texto = _texto(cliente.get(f"/gastos?{OCTUBRE}&categoria={id_servicios}"))
    assert "3 gastos" in texto and "S/ 550.30" in texto
    assert f'<option value="{id_servicios}" selected>' in texto


def test_cp16_sin_resultados_ofrece_limpiar_filtros(cliente, octubre):
    texto = _texto(cliente.get(f"/gastos?{OCTUBRE}&q=inexistente"))
    assert "No hay gastos con estos filtros" in texto
    assert "Limpiar filtros" in texto


def test_cp16_por_defecto_muestra_el_mes_actual(cliente, ana, cargar_gastos):
    hoy = hoy_lima()
    mes_pasado = hoy.replace(day=1) - timedelta(days=1)
    cargar_gastos(ana, [(hoy, "10.00", None, "Gasto de este mes", None),
                        (mes_pasado, "20.00", None, "Gasto del mes pasado", None)])
    texto = _texto(cliente.get("/gastos"))
    assert "Gasto de este mes" in texto
    assert "Gasto del mes pasado" not in texto
    assert f'value="{hoy.replace(day=1).isoformat()}"' in texto


def test_cp16_mes_sin_gastos_invita_a_registrar(cliente, ana):
    texto = _texto(cliente.get("/gastos"))
    assert "Aún no registras gastos este mes." in texto


def test_cp16_paginacion_de_50(cliente, ana, cargar_gastos):
    cargar_gastos(ana, [("2026-10-02", "1.00", None, None, None)] * 55)
    primera = _texto(cliente.get(f"/gastos?{OCTUBRE}"))
    assert primera.count("data-cg-gasto=") == 50
    assert "Página 1 de 2" in primera
    assert "55 gastos" in primera and "S/ 55.00" in primera
    segunda = _texto(cliente.get(f"/gastos?{OCTUBRE}&pagina=2"))
    assert segunda.count("data-cg-gasto=") == 5


def test_cp16_agrupa_por_dia_con_hoy_y_ayer(cliente, ana, cargar_gastos):
    hoy = hoy_lima()
    cargar_gastos(ana, [(hoy, "10.00", None, "A", None), (hoy, "5.50", None, "B", None),
                        (hoy - timedelta(days=1), "3.00", None, "C", None)])
    desde = (hoy - timedelta(days=1)).isoformat()
    texto = _texto(cliente.get(f"/gastos?desde={desde}&hasta={hoy.isoformat()}"))
    assert re.search(r">Hoy</h3>\s*<span[^>]*>S/ 15.50<", texto)
    assert re.search(r">Ayer</h3>\s*<span[^>]*>S/ 3.00<", texto)


# --- CP-17 Completitud del período y campo más omitido (RF-10) -------------------------------------------

def test_cp17_completitud_y_campo_mas_omitido(cliente, octubre):
    texto = _texto(cliente.get(f"/gastos?{OCTUBRE}"))
    assert "66.7 %" in texto
    assert "Dato más omitido: método de pago" in texto


def test_cp17_completitud_del_filtro(cliente, octubre):
    texto = _texto(cliente.get(f"/gastos?{OCTUBRE}&estado=completo"))
    assert "100.0 %" in texto
    assert "Todos los registros están completos" in texto


# --- CP-29 Gasto ajeno → 404; el administrador no tiene rutas de gastos -------------------------------------

def test_cp29_gasto_ajeno_responde_404(cliente, ana, crear_microemprendedor, cargar_gastos, sesion):
    luis = crear_microemprendedor("prueba.luis@ejemplo.com")
    (ajeno,) = cargar_gastos(luis, [("2026-10-01", "500.00", "Alquiler", "Ajeno", "Efectivo")])
    assert cliente.get(f"/gastos/{ajeno.id}/editar").status_code == 404
    assert cliente.post(f"/gastos/{ajeno.id}/editar", data=_datos()).status_code == 404
    assert cliente.post(f"/gastos/{ajeno.id}/eliminar").status_code == 404
    assert sesion.get(Gasto, ajeno.id).eliminado is False
    assert "Ajeno" not in _texto(cliente.get(f"/gastos?{OCTUBRE}"))


@pytest.mark.parametrize(("metodo", "ruta"), [("get", "/gastos"), ("get", "/gastos/nuevo"), ("post", "/gastos/nuevo")])
def test_cp29_administrador_no_tiene_rutas_de_gastos(cliente, crear_admin, iniciar_sesion, metodo, ruta):
    crear_admin()
    iniciar_sesion("prueba.admin@ejemplo.com")
    assert getattr(cliente, metodo)(ruta).status_code == 403


def test_cp29_sin_sesion_redirige_al_login(cliente, sesion):
    assert cliente.get("/gastos").headers["Location"].startswith("/login")


# --- Registro rápido desde el inicio y navegación (RNF-05) ----------------------------------------------------

def test_registro_rapido_en_el_inicio(cliente, ana, sesion):
    texto = _texto(cliente.get("/"))
    assert "¿En qué gastaste?" in texto
    assert 'action="/gastos/nuevo?next=/"' in texto
    assert 'aria-label="Registrar gasto"' in texto  # FAB a un toque del formulario

    respuesta = cliente.post("/gastos/nuevo?next=/", data=_datos(monto="7.50"))
    assert respuesta.headers["Location"] == "/"
    assert _cantidad_gastos(sesion, usuario_id=ana.id) == 1


def test_registro_rapido_con_error_muestra_el_formulario_completo(cliente, ana):
    respuesta = cliente.post("/gastos/nuevo?next=/", data=_datos(monto=""))
    texto = _texto(respuesta)
    assert "Escribe el monto del gasto." in texto
    assert "Registrar gasto" in texto


def test_no_redirige_a_sitios_externos_tras_guardar(cliente, ana):
    respuesta = cliente.post("/gastos/nuevo?next=https://malicioso.com", data=_datos())
    assert respuesta.headers["Location"] == "/gastos"


def test_menu_muestra_mis_gastos(cliente, ana):
    texto = _texto(cliente.get("/gastos"))
    assert "Mis gastos" in texto
    assert 'aria-current="page"' in texto
