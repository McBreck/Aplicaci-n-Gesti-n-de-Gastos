"""CU-09 y CU-10: categorías, presupuesto mensual, comparación y alertas (CP-18 a CP-21)."""
import re
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models import Categoria, Presupuesto
from app.services.formato import hoy_lima
from tests.datos_verificacion import GASTOS_OCTUBRE_2026, PRESUPUESTO_OCTUBRE_2026


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


def _texto(respuesta) -> str:
    return respuesta.get_data(as_text=True)


def _mes_actual() -> date:
    return hoy_lima().replace(day=1)


# --- CP-18 Crear y renombrar categorías propias (RF-11) ----------------------------------------

def test_cp18_listado_de_categorias(cliente, ana):
    texto = _texto(cliente.get("/categorias"))
    assert texto.count("Predeterminada</span>") == 9
    assert "Renombrar" not in texto  # las predeterminadas no se renombran
    assert texto.count('role="switch"') == 9
    assert texto.count('name="color"') == 10  # paleta de la sección 11.1


def test_cp18_crear_categoria(cliente, ana, sesion):
    respuesta = cliente.post("/categorias", data={"nombre": "Delivery", "color": "#C4B5FD"}, follow_redirects=True)
    texto = _texto(respuesta)
    assert "Categoría «Delivery» creada." in texto
    assert "Renombrar" in texto
    nueva = sesion.scalar(select(Categoria).where(Categoria.usuario_id == ana.id, Categoria.nombre == "Delivery"))
    assert nueva.color == "#C4B5FD" and nueva.predeterminada is False


def test_cp18_nombre_repetido_sin_distinguir_mayusculas(cliente, ana):
    respuesta = cliente.post("/categorias", data={"nombre": "oTrOs", "color": "#8B7BFF"})
    texto = _texto(respuesta)
    assert respuesta.status_code == 200
    assert "Ya tienes una categoría con ese nombre" in texto
    assert 'value="oTrOs"' in texto


def test_cp18_renombrar_propia_y_rechazar_duplicado(cliente, ana, sesion):
    cliente.post("/categorias", data={"nombre": "Delivery", "color": "#C4B5FD"})
    delivery = sesion.scalar(select(Categoria).where(Categoria.nombre == "Delivery"))
    respuesta = cliente.post(f"/categorias/{delivery.id}/editar", data={"nombre": "Envíos"}, follow_redirects=True)
    assert "Categoría renombrada." in _texto(respuesta)
    assert delivery.nombre == "Envíos"

    rechazo = _texto(cliente.post(f"/categorias/{delivery.id}/editar", data={"nombre": "ALQUILER"}))
    assert "Ya tienes una categoría con ese nombre" in rechazo
    assert f'class="collapse show" id="renombrar-{delivery.id}"' in rechazo
    assert delivery.nombre == "Envíos"


def test_cp18_una_predeterminada_no_se_renombra(cliente, ana, id_categoria, sesion):
    id_otros = id_categoria(ana, "Otros")
    respuesta = cliente.post(f"/categorias/{id_otros}/editar", data={"nombre": "Varios"}, follow_redirects=True)
    assert "Las categorías predeterminadas no se pueden renombrar." in _texto(respuesta)
    assert sesion.get(Categoria, id_otros).nombre == "Otros"


# --- CP-19 Desactivar: no aparece al registrar, se conserva en el historial ----------------------

def test_cp19_desactivar_y_reactivar(cliente, ana, cargar_gastos, id_categoria, sesion):
    hoy = hoy_lima()
    (gasto,) = cargar_gastos(ana, [(hoy, "35.00", "Mantenimiento", "Repuesto", "Efectivo")])
    id_mant = id_categoria(ana, "Mantenimiento")

    respuesta = cliente.post(f"/categorias/{id_mant}/estado", follow_redirects=True)
    assert "Categoría «Mantenimiento» desactivada." in _texto(respuesta)
    assert 'aria-checked="false"' in _texto(respuesta)
    assert "Mantenimiento" not in _texto(cliente.get("/gastos/nuevo"))
    lista = _texto(cliente.get("/gastos"))
    assert ">Mantenimiento</span>" in lista  # el gasto anterior conserva su categoría
    assert sesion.get(type(gasto), gasto.id).categoria_id == id_mant

    cliente.post(f"/categorias/{id_mant}/estado")
    assert "Mantenimiento" in _texto(cliente.get("/gastos/nuevo"))


# --- CP-20 Presupuesto mensual y copia del mes anterior (RF-12, RN-10) ----------------------------

def test_cp20_ver_y_guardar_presupuesto(cliente, ana, sesion, id_categoria):
    texto = _texto(cliente.get("/presupuesto?mes=2026-10"))
    assert "Octubre 2026" in texto
    assert texto.count('placeholder="Sin presupuesto"') == 9

    insumos, alquiler = id_categoria(ana, "Insumos y materia prima"), id_categoria(ana, "Alquiler")
    respuesta = cliente.post(
        "/presupuesto?mes=2026-10", data={f"monto_{insumos}": "400", f"monto_{alquiler}": "900.00"}
    )
    assert respuesta.headers["Location"] == "/presupuesto?mes=2026-10"
    texto = _texto(cliente.get("/presupuesto?mes=2026-10"))
    assert "Presupuesto de Octubre 2026 guardado." in texto
    assert 'value="400.00"' in texto and 'value="900.00"' in texto
    assert "S/ 1,300.00" in texto  # total planificado

    # Vacío = sin presupuesto
    cliente.post("/presupuesto?mes=2026-10", data={f"monto_{insumos}": "", f"monto_{alquiler}": "900"})
    montos = sesion.scalars(select(Presupuesto.monto).where(Presupuesto.usuario_id == ana.id)).all()
    assert montos == [Decimal("900.00")]


def test_cp20_montos_invalidos_se_muestran_por_fila(cliente, ana, sesion, id_categoria):
    alquiler = id_categoria(ana, "Alquiler")
    texto = _texto(cliente.post("/presupuesto?mes=2026-10", data={f"monto_{alquiler}": "-5"}))
    assert "El monto no puede ser negativo." in texto
    assert 'value="-5"' in texto
    assert sesion.scalar(select(Presupuesto)) is None


def test_cp20_copiar_del_mes_anterior(cliente, ana, presupuestar):
    presupuestar(ana, PRESUPUESTO_OCTUBRE_2026, date(2026, 10, 1))
    respuesta = cliente.post("/presupuesto/copiar?mes=2026-11", follow_redirects=True)
    texto = _texto(respuesta)
    assert "Se copiaron 5 montos de Octubre 2026." in texto
    assert 'value="520.00"' in texto and "Noviembre 2026" in texto


def test_cp20_copiar_sin_presupuesto_previo(cliente, ana):
    texto = _texto(cliente.post("/presupuesto/copiar?mes=2026-11", follow_redirects=True))
    assert "Octubre 2026 no tiene presupuesto para copiar." in texto


def test_cp20_mes_fuera_de_rango_es_solo_lectura(cliente, ana, id_categoria):
    texto = _texto(cliente.get("/presupuesto?mes=2025-12"))
    assert "desde enero de 2026" in texto
    assert "disabled" in texto
    assert "Copiar del mes anterior" not in texto
    respuesta = cliente.post("/presupuesto?mes=2025-12", data={f"monto_{id_categoria(ana, 'Alquiler')}": "1"},
                             follow_redirects=True)
    assert "desde enero de 2026" in _texto(respuesta)


# --- CP-21 Comparación ejecutado vs. planificado y alertas (RF-13, RF-14) ---------------------------

def test_cp21_comparacion_con_los_datos_de_verificacion(cliente, ana, cargar_gastos, presupuestar):
    cargar_gastos(ana, GASTOS_OCTUBRE_2026)
    presupuestar(ana, PRESUPUESTO_OCTUBRE_2026, date(2026, 10, 1))
    texto = _texto(cliente.get("/presupuesto?mes=2026-10"))
    assert "Servicios (luz, agua, gas) superó su presupuesto: S/ 550.30 de S/ 520.00 (105.8 %)." in texto
    assert "Empaques y envases llegó al 83.3 % de su presupuesto" in texto
    assert "Alquiler llegó al 100.0 % de su presupuesto" in texto
    assert "94.5 %" in texto  # A9
    assert "S/ 1,930.00" in texto and "S/ 1,824.80" in texto
    assert "También gastaste S/ 42.00 sin categoría" in texto
    chips = re.findall(
        r'cg-chip cg-chip--\w+">\s*<i class="bi [\w-]+" aria-hidden="true"></i>(Controlada|En alerta|Excedida)', texto
    )
    # Orden de las filas: Insumos, Servicios, Alquiler, Transporte, Empaques (+ estado general)
    assert chips.count("Excedida") == 1 and chips.count("Controlada") == 2


def test_cp21_limites_y_alertas_en_la_navegacion(cliente, ana, cargar_gastos, presupuestar):
    mes = _mes_actual()
    hoy = hoy_lima()
    presupuestar(
        ana, {"Insumos y materia prima": "100", "Mercadería": "100", "Alquiler": "100", "Transporte": "100"}, mes
    )
    cargar_gastos(ana, [(hoy, "79.90", "Insumos y materia prima", "a", "Efectivo"),
                        (hoy, "80.00", "Mercadería", "b", "Efectivo"),
                        (hoy, "100.00", "Alquiler", "c", "Efectivo"),
                        (hoy, "100.10", "Transporte", "d", "Efectivo")])
    texto = _texto(cliente.get("/presupuesto"))
    for porcentaje in ("79.9 %", "80.0 %", "100.0 %", "100.1 %"):
        assert porcentaje in texto
    assert "Transporte superó su presupuesto" in texto
    assert "Insumos y materia prima llegó" not in texto  # al 79.9 % no hay alerta

    inicio = _texto(cliente.get("/"))
    assert re.search(r'cg-nav__badge">3<span class="visually-hidden"> categorías en alerta o excedidas', inicio)
    assert "Has usado el 90.0 %" in inicio  # widget del mes actual: 360.00 de 400.00
    assert "Ver presupuesto" in inicio


def test_barra_lateral_sin_presupuesto(cliente, ana, cargar_gastos):
    cargar_gastos(ana, [(hoy_lima(), "12.50", "Transporte", "Pasaje", "Efectivo")])
    texto = _texto(cliente.get("/"))
    assert "Aún no defines tu presupuesto" in texto
    assert "Definir presupuesto" in texto
    assert "cg-nav__badge" not in texto
    assert re.search(r"Transporte</span>\s*<span class=\"cg-lateral__categoria-monto cg-numero\">S/ 12.50", texto)


# --- Control de acceso (CP-29) -----------------------------------------------------------------------

@pytest.mark.parametrize(("metodo", "ruta"), [("get", "/categorias"), ("post", "/categorias"),
                                              ("get", "/presupuesto"), ("post", "/presupuesto/copiar")])
def test_cp29_administrador_no_gestiona_categorias_ni_presupuesto(cliente, crear_admin, iniciar_sesion, metodo, ruta):
    crear_admin()
    iniciar_sesion("prueba.admin@ejemplo.com")
    assert getattr(cliente, metodo)(ruta).status_code == 403


def test_cp29_categoria_ajena_responde_404(cliente, ana, crear_microemprendedor, id_categoria, sesion):
    luis = crear_microemprendedor("prueba.luis@ejemplo.com")
    ajena = id_categoria(luis, "Alquiler")
    assert cliente.post(f"/categorias/{ajena}/estado").status_code == 404
    assert cliente.post(f"/categorias/{ajena}/editar", data={"nombre": "X"}).status_code == 404
    assert sesion.get(Categoria, ajena).activa is True
