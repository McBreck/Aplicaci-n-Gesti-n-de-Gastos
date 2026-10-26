"""PresupuestoService (RF-12 a RF-14; RN-05, RN-06, RN-10), meses y montos con cero."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.models import Auditoria, Categoria, Presupuesto
from app.services import presupuesto as presupuesto_service
from app.services.periodo import interpretar_mes, mes_anterior, mes_siguiente, texto_mes, ultimo_dia
from app.services.presupuesto import FilaPresupuesto
from app.services.validacion import ErrorValidacion, interpretar_monto
from tests.datos_verificacion import GASTOS_OCTUBRE_2026, PRESUPUESTO_OCTUBRE_2026

OCTUBRE = date(2026, 10, 1)
HOY = date(2026, 10, 26)


# --- Meses ---------------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("2026-10", date(2026, 10, 1)), ("2027-01", date(2027, 1, 1)), ("", date(2026, 10, 1)),
     (None, date(2026, 10, 1)), ("2026-13", date(2026, 10, 1)), ("octubre", date(2026, 10, 1)),
     ("1999-05", date(2026, 10, 1)), ("2026-10-05", date(2026, 10, 1))],
)
def test_interpretar_mes(texto, esperado):
    assert interpretar_mes(texto, HOY) == esperado


def test_limites_del_mes():
    assert ultimo_dia(date(2026, 2, 1)) == date(2026, 2, 28)
    assert ultimo_dia(date(2028, 2, 1)) == date(2028, 2, 29)
    assert mes_anterior(date(2026, 1, 1)) == date(2025, 12, 1)
    assert mes_siguiente(date(2026, 12, 1)) == date(2027, 1, 1)
    assert texto_mes(date(2026, 3, 1)) == "2026-03"


def test_monto_del_presupuesto_admite_cero_pero_no_negativos():
    assert interpretar_monto("0", permitir_cero=True) == Decimal("0.00")
    assert interpretar_monto("1,250.5", permitir_cero=True) == Decimal("1250.50")
    with pytest.raises(ValueError, match="no puede ser negativo"):
        interpretar_monto("-10", permitir_cero=True)
    with pytest.raises(ValueError, match="mayor que cero"):
        interpretar_monto("0")


# --- Estados por categoría (RN-05, RN-06) ----------------------------------------------------

def _fila(planificado, ejecutado):
    categoria = SimpleNamespace(id=1, nombre="X", color="#8B7BFF", activa=True)
    planificado = None if planificado is None else Decimal(planificado)
    return FilaPresupuesto(categoria, planificado, Decimal(ejecutado))


@pytest.mark.parametrize(
    ("ejecutado", "estado", "porcentaje"),
    [("79.90", "Controlada", 79.9), ("80.00", "En alerta", 80.0),
     ("100.00", "En alerta", 100.0), ("100.10", "Excedida", 100.1)],
)
def test_limites_79_9_80_100_100_1(ejecutado, estado, porcentaje):
    fila = _fila("100.00", ejecutado)
    assert (fila.estado, fila.porcentaje) == (estado, porcentaje)
    assert fila.en_alerta is (estado != "Controlada")


def test_fila_sin_presupuesto_o_en_cero():
    sin = _fila(None, "50")
    assert (sin.tiene_presupuesto, sin.estado, sin.porcentaje, sin.porcentaje_barra) == (False, None, None, 0.0)
    cero = _fila("0", "5")
    assert (cero.estado, cero.porcentaje, cero.porcentaje_barra) == ("Excedida", None, 125.0)
    assert _fila("0", "0").estado == "Controlada"


def test_la_barra_se_corta_en_125():
    assert _fila("100", "300").porcentaje_barra == 125.0
    assert _fila("100", "50").porcentaje_barra == 50.0


# --- Comparación con los datos de verificación (Ficha de registro N.° 1) ------------------------

@pytest.fixture
def ana(crear_microemprendedor):
    return crear_microemprendedor()


@pytest.fixture
def presupuestar(sesion, id_categoria):
    def _presupuestar(usuario, montos: dict, mes: date = OCTUBRE):
        for nombre, monto in montos.items():
            sesion.add(Presupuesto(usuario_id=usuario.id, categoria_id=id_categoria(usuario, nombre),
                                   anio=mes.year, mes=mes.month, monto=Decimal(monto)))
        sesion.commit()
    return _presupuestar


@pytest.fixture
def octubre(ana, cargar_gastos, presupuestar):
    cargar_gastos(ana, GASTOS_OCTUBRE_2026)
    presupuestar(ana, PRESUPUESTO_OCTUBRE_2026)


def test_comparacion_de_octubre(ana, octubre):
    comparacion = presupuesto_service.comparar(ana.id, OCTUBRE)
    filas = {fila.categoria.nombre: fila for fila in comparacion.con_presupuesto}
    esperado = {
        "Insumos y materia prima": ("318.50", 79.6, "Controlada"),
        "Servicios (luz, agua, gas)": ("550.30", 105.8, "Excedida"),
        "Empaques y envases": ("50.00", 83.3, "En alerta"),
        "Alquiler": ("900.00", 100.0, "En alerta"),
        "Transporte": ("6.00", 12.0, "Controlada"),
    }
    for nombre, (ejecutado, porcentaje, estado) in esperado.items():
        fila = filas[nombre]
        assert (fila.ejecutado, fila.porcentaje, fila.estado) == (Decimal(ejecutado), porcentaje, estado)

    assert comparacion.controladas == 4  # 4 de 5 categorías controladas
    assert comparacion.total_planificado == Decimal("1930.00")
    assert comparacion.total_ejecutado == Decimal("1824.80")
    assert comparacion.porcentaje_usado == 94.5  # A9
    assert comparacion.estado_general == "En alerta"
    assert comparacion.sin_categoria == Decimal("42.00")
    assert comparacion.total_mes == Decimal("1866.80")
    assert [fila.categoria.nombre for fila in comparacion.alertas][0] == "Servicios (luz, agua, gas)"
    assert len(comparacion.alertas) == 3
    assert len(comparacion.filas) == 9  # todas las activas, con o sin presupuesto


def test_comparacion_sin_presupuesto(ana):
    comparacion = presupuesto_service.comparar(ana.id, OCTUBRE)
    assert not comparacion.tiene_presupuesto
    assert comparacion.porcentaje_usado is None
    assert comparacion.estado_general is None
    assert comparacion.alertas == []


def test_barra_general_sin_presupuesto_o_con_montos_en_cero(ana, presupuestar, cargar_gastos):
    assert presupuesto_service.comparar(ana.id, OCTUBRE).porcentaje_barra == 0.0
    presupuestar(ana, {"Alquiler": "0"})
    assert presupuesto_service.comparar(ana.id, OCTUBRE).porcentaje_barra == 0.0
    cargar_gastos(ana, [("2026-10-04", "10.00", "Alquiler", "x", "Efectivo")])
    comparacion = presupuesto_service.comparar(ana.id, OCTUBRE)
    assert (comparacion.porcentaje_usado, comparacion.porcentaje_barra, comparacion.estado_general) == (
        None, 125.0, "Excedida")


def test_categoria_inactiva_con_presupuesto_sigue_en_la_comparacion(ana, sesion, presupuestar, id_categoria):
    presupuestar(ana, {"Otros": "10.00"})
    sesion.get(Categoria, id_categoria(ana, "Otros")).activa = False
    sesion.get(Categoria, id_categoria(ana, "Mercadería")).activa = False
    sesion.commit()
    nombres = [fila.categoria.nombre for fila in presupuesto_service.comparar(ana.id, OCTUBRE).filas]
    assert "Otros" in nombres and "Mercadería" not in nombres


# --- Guardar (RF-12, RN-10) --------------------------------------------------------------------

def _presupuestos(sesion, usuario, mes=OCTUBRE):
    consulta = select(Categoria.nombre, Presupuesto.monto).join(Categoria).where(
        Presupuesto.usuario_id == usuario.id, Presupuesto.anio == mes.year, Presupuesto.mes == mes.month
    )
    return {nombre: monto for nombre, monto in sesion.execute(consulta)}


def test_guardar_crea_actualiza_y_borra(ana, sesion, id_categoria):
    insumos, servicios = id_categoria(ana, "Insumos y materia prima"), id_categoria(ana, "Servicios (luz, agua, gas)")
    assert presupuesto_service.guardar_presupuesto(ana, OCTUBRE, {insumos: "400", servicios: "0"}) == 2
    assert _presupuestos(sesion, ana) == {"Insumos y materia prima": Decimal("400.00"), "Servicios (luz, agua, gas)": Decimal("0.00")}

    assert presupuesto_service.guardar_presupuesto(ana, OCTUBRE, {insumos: "450,50", servicios: ""}) == 2
    assert _presupuestos(sesion, ana) == {"Insumos y materia prima": Decimal("450.50")}

    # Sin cambios: no se registra nada nuevo y sigue habiendo un solo presupuesto por categoría (RN-10)
    assert presupuesto_service.guardar_presupuesto(ana, OCTUBRE, {insumos: "450.50"}) == 0
    assert sesion.scalar(select(func.count(Presupuesto.id))) == 1
    eventos = sesion.scalars(
        select(Auditoria).where(Auditoria.entidad == "presupuesto").order_by(Auditoria.id)
    ).all()
    assert len(eventos) == 2
    assert eventos[1].detalle["anterior"] == {str(insumos): "400.00", str(servicios): "0.00"}
    assert eventos[1].detalle["nuevo"] == {str(insumos): "450.50", str(servicios): None}


def test_guardar_con_errores_no_cambia_nada(ana, sesion, id_categoria):
    insumos, alquiler = id_categoria(ana, "Insumos y materia prima"), id_categoria(ana, "Alquiler")
    with pytest.raises(ErrorValidacion) as error:
        presupuesto_service.guardar_presupuesto(ana, OCTUBRE, {insumos: "400", alquiler: "-5"})
    assert error.value.errores == {str(alquiler): "El monto no puede ser negativo."}
    assert _presupuestos(sesion, ana) == {}


def test_guardar_ignora_categorias_ajenas(ana, crear_microemprendedor, sesion, id_categoria):
    luis = crear_microemprendedor("prueba.luis@ejemplo.com")
    ajena = id_categoria(luis, "Alquiler")
    assert presupuesto_service.guardar_presupuesto(ana, OCTUBRE, {ajena: "500"}) == 0
    assert sesion.scalar(select(func.count(Presupuesto.id))) == 0


def test_no_se_guarda_fuera_del_rango_2026_2100(ana, id_categoria):
    with pytest.raises(presupuesto_service.ErrorPresupuesto, match="desde enero de 2026"):
        presupuesto_service.guardar_presupuesto(ana, date(2025, 12, 1), {id_categoria(ana, "Alquiler"): "1"})


# --- Copiar del mes anterior (flujo alterno 3a) --------------------------------------------------

def test_copiar_replica_los_montos(ana, sesion, presupuestar, id_categoria):
    presupuestar(ana, PRESUPUESTO_OCTUBRE_2026)
    noviembre = date(2026, 11, 1)
    presupuestar(ana, {"Alquiler": "950.00", "Mercadería": "300.00"}, noviembre)
    sesion.get(Categoria, id_categoria(ana, "Transporte")).activa = False
    sesion.commit()

    assert presupuesto_service.copiar_mes_anterior(ana, noviembre) == 4  # Transporte está inactiva
    copiados = _presupuestos(sesion, ana, noviembre)
    assert copiados["Alquiler"] == Decimal("900.00")  # reemplazado
    assert copiados["Mercadería"] == Decimal("300.00")  # se conserva
    assert copiados["Insumos y materia prima"] == Decimal("400.00")
    assert "Transporte" not in copiados
    evento = sesion.scalar(select(Auditoria).where(Auditoria.entidad == "presupuesto"))
    assert evento.detalle["copiado_de"] == "2026-10"


def test_copiar_sin_presupuesto_previo(ana):
    with pytest.raises(presupuesto_service.ErrorPresupuesto, match="Octubre 2026 no tiene presupuesto para copiar."):
        presupuesto_service.copiar_mes_anterior(ana, date(2026, 11, 1))
    with pytest.raises(presupuesto_service.ErrorPresupuesto, match="Diciembre 2025"):
        presupuesto_service.copiar_mes_anterior(ana, date(2026, 1, 1))
    with pytest.raises(presupuesto_service.ErrorPresupuesto, match="desde enero de 2026"):
        presupuesto_service.copiar_mes_anterior(ana, date(2025, 6, 1))
