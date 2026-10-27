"""Datos de demostración PRUEBA: plan de 60 días, presupuestos, creación y borrado completo."""
from collections import Counter
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app import demo
from app.models import Auditoria, Categoria, Gasto, Presupuesto, Usuario
from app.models.presupuesto import ESTADO_EN_ALERTA, ESTADO_EXCEDIDA
from app.services import analitica, auditoria
from app.services.usuario import ErrorUsuario

HOY = date(2026, 10, 26)
CONTRASENA = "Demo2026"


def _contar(sesion, modelo, *condiciones) -> int:
    return sesion.scalar(select(func.count()).select_from(modelo).where(*condiciones))


# --- Plan de gastos y presupuestos -----------------------------------------------------------

def test_plan_reproducible_de_60_dias_sin_fechas_futuras():
    gastos = demo.planificar_gastos(HOY)
    assert gastos == demo.planificar_gastos(HOY)  # misma fecha, mismos datos
    assert (gastos[0].fecha, gastos[-1].fecha) == (date(2026, 8, 28), HOY)  # 60 días; RN-04: nada futuro
    assert all(gasto.monto > 0 and gasto.monto == gasto.monto.quantize(Decimal("0.01")) for gasto in gastos)


def test_gastos_variados_con_incompletos():
    gastos = demo.planificar_gastos(HOY)
    assert {gasto.categoria for gasto in gastos} - {None} == set(demo.PRESUPUESTO_MENSUAL) | {"Otros"}
    assert len({gasto.metodo for gasto in gastos} - {None}) == 5
    incompletos = [gasto for gasto in gastos if None in (gasto.categoria, gasto.descripcion, gasto.metodo)]
    assert 0.1 <= len(incompletos) / len(gastos) <= 0.3
    omitidos = Counter(
        campo
        for gasto in incompletos
        for campo in ("categoria", "descripcion", "metodo")
        if getattr(gasto, campo) is None
    )
    assert omitidos.most_common(1)[0][0] == "metodo"  # A8: el método de pago es el dato más omitido


def test_gastos_fijos_en_su_dia():
    gastos = demo.planificar_gastos(HOY)
    alquileres = [gasto.fecha for gasto in gastos if gasto.monto == Decimal("900.00")]
    assert alquileres == [date(2026, 9, 1), date(2026, 10, 1)]
    sabados = {gasto.fecha.weekday() for gasto in gastos if gasto.descripcion == "Pago semanal al ayudante"}
    assert sabados == {5}


@pytest.mark.parametrize(
    ("hoy", "meses", "con_presupuesto"),
    [
        (HOY, [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)], [date(2026, 8, 1), date(2026, 9, 1),
                                                                        date(2026, 10, 1)]),
        # El presupuesto solo se define desde enero de 2026 (CHECK de la tabla presupuesto)
        (date(2026, 1, 20), [date(2025, 11, 1), date(2025, 12, 1), date(2026, 1, 1)], [date(2026, 1, 1)]),
    ],
)
def test_meses_del_periodo(hoy, meses, con_presupuesto):
    assert demo.meses_del_periodo(hoy) == meses
    assert demo.meses_con_presupuesto(hoy) == con_presupuesto


# --- Rendimiento (CP-28) -------------------------------------------------------------------------

SEPTIEMBRE = date(2026, 9, 1)


def test_plan_de_rendimiento_con_500_gastos_en_el_mes():
    gastos = demo.planificar_rendimiento(SEPTIEMBRE, HOY)
    assert len(gastos) == 500 and gastos == demo.planificar_rendimiento(SEPTIEMBRE, HOY)
    assert (gastos[0].fecha, gastos[-1].fecha) == (SEPTIEMBRE, date(2026, 9, 30))
    assert len({gasto.fecha for gasto in gastos}) == 30  # todos los días del mes
    assert {gasto.categoria for gasto in gastos} - {None} == set(demo.PRESUPUESTO_MENSUAL) | {"Otros"}
    # Los gastos fijos caen en su día: un solo alquiler, el 1 del mes
    assert [gasto.fecha for gasto in gastos if gasto.monto == Decimal("900.00")] == [SEPTIEMBRE]


def test_rendimiento_del_mes_en_curso_hasta_hoy():
    gastos = demo.planificar_rendimiento(date(2026, 10, 1), HOY)
    assert len(gastos) == 500 and gastos[-1].fecha == HOY


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [(None, SEPTIEMBRE), ("", SEPTIEMBRE), ("2026-08", date(2026, 8, 1)), (" 2026-10 ", date(2026, 10, 1))],
)
def test_mes_de_rendimiento(texto, esperado):
    assert demo.mes_de_rendimiento(texto, HOY) == esperado


@pytest.mark.parametrize(
    ("texto", "mensaje"),
    [("2026-11", "posterior al actual"), ("septiembre", "AAAA-MM"), ("2026-13", "AAAA-MM"), ("2026-09-01", "AAAA-MM")],
)
def test_mes_de_rendimiento_invalido(texto, mensaje):
    with pytest.raises(demo.ErrorDemo, match=mensaje):
        demo.mes_de_rendimiento(texto, HOY)


# --- Creación ------------------------------------------------------------------------------------

def test_crear_la_cuenta_de_demostracion(sesion):
    resumen = demo.crear(CONTRASENA, HOY)
    usuario = sesion.scalar(select(Usuario).where(Usuario.correo == demo.CORREO))
    assert (usuario.nombre, usuario.nombre_negocio, usuario.rubro, usuario.rol) == (
        "PRUEBA Panadería", "PRUEBA Panadería", "Panadería", "microemprendedor")
    assert usuario.verificar_contrasena(CONTRASENA)
    assert _contar(sesion, Categoria, Categoria.usuario_id == usuario.id) == 9  # RN-11
    assert resumen.gastos == len(demo.planificar_gastos(HOY)) == _contar(sesion, Gasto, Gasto.usuario_id == usuario.id)
    assert resumen.incompletos == _contar(sesion, Gasto, Gasto.usuario_id == usuario.id, Gasto.es_completo.is_(False))
    assert resumen.presupuestos == 3 * 8 == _contar(sesion, Presupuesto, Presupuesto.usuario_id == usuario.id)
    assert (resumen.desde, resumen.hasta) == (date(2026, 8, 28), HOY)
    evento = sesion.scalar(select(Auditoria).where(Auditoria.entidad_id == usuario.id))
    assert (evento.accion, evento.detalle["origen"]) == ("CREAR", "flask demo crear")


def test_la_demostracion_muestra_alertas_proyeccion_y_recomendaciones(sesion):
    demo.crear(CONTRASENA, HOY)
    usuario = sesion.scalar(select(Usuario).where(Usuario.correo == demo.CORREO))
    analisis = analitica.analizar_mes(usuario.id, HOY.replace(day=1), HOY)
    assert analisis.completitud.porcentaje_completitud < 100
    assert analisis.completitud.campo_mas_omitido == "método de pago"
    assert analisis.proyeccion.suficiente  # P1 con más de 7 días y 10 registros
    assert {ESTADO_EN_ALERTA, ESTADO_EXCEDIDA} <= {fila["estado"] for fila in analisis.mayor_ejecucion(8)}
    assert analisis.recomendaciones


def test_crear_la_cuenta_de_rendimiento(sesion):
    resumen = demo.crear_rendimiento(CONTRASENA, SEPTIEMBRE, HOY)
    usuario = sesion.scalar(select(Usuario).where(Usuario.correo == demo.CORREO_RENDIMIENTO))
    assert (usuario.nombre, usuario.nombre_negocio) == ("PRUEBA Rendimiento", "PRUEBA Rendimiento")
    assert resumen.gastos == 500 == _contar(sesion, Gasto, Gasto.usuario_id == usuario.id)
    assert (resumen.desde, resumen.hasta, resumen.presupuestos) == (SEPTIEMBRE, date(2026, 9, 30), 0)
    with pytest.raises(demo.ErrorDemo, match="ya existe"):
        demo.crear_rendimiento(CONTRASENA, SEPTIEMBRE, HOY)
    # Convive con la cuenta de demostración y `demo borrar` elimina las dos
    demo.crear(CONTRASENA, HOY)
    assert demo.borrar().cuentas == 2


def test_no_se_crea_dos_veces_ni_con_una_contrasena_debil(sesion):
    with pytest.raises(ErrorUsuario):
        demo.crear("corta", HOY)
    assert _contar(sesion, Usuario) == 0
    demo.crear(CONTRASENA, HOY)
    with pytest.raises(demo.ErrorDemo, match="ya existe"):
        demo.crear(CONTRASENA, HOY)
    assert _contar(sesion, Usuario) == 1


# --- Borrado -------------------------------------------------------------------------------------

def test_borrar_elimina_todo_lo_prueba_y_conserva_las_demas_cuentas(sesion, crear_microemprendedor, crear_admin,
                                                                    cargar_gastos):
    resumen_demo = demo.crear(CONTRASENA, HOY)
    ana = crear_microemprendedor()
    cargar_gastos(ana, [("2026-10-05", "10.00", "Transporte", "Mototaxi", "Efectivo")])
    crear_admin()
    # Única cuenta sin el prefijo PRUEBA: comprueba que el borrado no toca las cuentas reales
    real = crear_microemprendedor("rosa.diaz@ejemplo.com", nombre="Rosa Díaz")
    cargar_gastos(real, [("2026-10-05", "20.00", "Alquiler", "Alquiler", "Efectivo")])
    auditoria.registrar(auditoria.INICIO_SESION, "usuario", usuario_id=real.id, entidad_id=real.id)
    sesion.commit()

    resumen = demo.borrar()
    assert resumen == demo.ResumenBorrado(
        cuentas=3, gastos=resumen_demo.gastos + 1, presupuestos=24, categorias=18, eventos=1)
    assert sesion.scalars(select(Usuario.correo)).all() == ["rosa.diaz@ejemplo.com"]
    assert _contar(sesion, Gasto) == 1 and _contar(sesion, Auditoria) == 1
    assert _contar(sesion, Categoria, Categoria.usuario_id.is_(None)) == 9  # la plantilla se conserva
    assert demo.borrar() == demo.ResumenBorrado()


def test_las_cuentas_prueba_se_reconocen_por_el_nombre(sesion, crear_usuario):
    crear_usuario("prueba.uno@ejemplo.com", nombre="PRUEBA Uno")
    crear_usuario("dos@ejemplo.com", nombre="Prueba de sabor", nombre_negocio="PRUEBA Dos")
    assert [cuenta.correo for cuenta in demo.cuentas_prueba()] == ["prueba.uno@ejemplo.com"]
