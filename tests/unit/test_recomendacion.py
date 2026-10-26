"""RecomendacionService: reglas R1–R7, prioridad y máximo de tres (RF-18, RN-08)."""
from datetime import date
from decimal import Decimal

from app.services import recomendacion
from app.services.gasto import ResumenGastos
from app.services.proyeccion import Proyeccion, proyectar
from app.services.recomendacion import DatosRecomendacion, EjecucionCategoria, GastoCategoria
from tests.datos_verificacion import ACUMULADO_25_DIAS

OCTUBRE = date(2026, 10, 1)
HOY = date(2026, 10, 26)
COMPLETA = ResumenGastos(cantidad=10, completos=10, faltantes={})
SIN_PROYECCION = Proyeccion(suficiente=False)


def _ejecucion(categoria_id, nombre, planificado, ejecutado, porcentaje, estado):
    return EjecucionCategoria(categoria_id, nombre, Decimal(planificado), Decimal(ejecutado), porcentaje, estado)


def _categoria(categoria_id, nombre, total, anterior="0", participacion=10.0):
    return GastoCategoria(categoria_id, nombre, Decimal(total), Decimal(anterior), participacion)


def _datos(**cambios) -> DatosRecomendacion:
    base = {"mes": OCTUBRE, "hoy": HOY, "ejecucion": (), "categorias": (), "completitud": COMPLETA,
            "proyeccion": SIN_PROYECCION, "ultima_fecha": HOY}
    return DatosRecomendacion(**{**base, **cambios})


def _mensajes(datos) -> list[str]:
    return [r.mensaje for r in recomendacion.generar(datos)]


def test_sin_condiciones_los_gastos_estan_bajo_control():
    assert recomendacion.generar(_datos()) == []
    assert recomendacion.MENSAJE_BAJO_CONTROL == "Tus gastos están bajo control este mes"


def test_r2_categoria_excedida():
    datos = _datos(ejecucion=(_ejecucion(3, "Servicios (luz, agua, gas)", "520.00", "550.30", 105.8, "Excedida"),))
    (r2,) = recomendacion.generar(datos)
    assert r2.regla == "R2" and r2.prioridad == 1
    assert r2.mensaje == "Servicios (luz, agua, gas) superó su presupuesto en S/ 30.30 (5.8 %)."
    assert (r2.accion, r2.endpoint) == ("Ver gastos de la categoría", "gastos.listar")
    assert r2.argumentos == {"categoria": 3, "desde": "2026-10-01", "hasta": "2026-10-31"}


def test_r3_proyeccion_por_encima_del_presupuesto():
    datos = _datos(
        ejecucion=(_ejecucion(1, "Insumos", "2400.00", "900.00", 37.5, "Controlada"),
                   _ejecucion(4, "Alquiler", "2400.00", "900.00", 37.5, "Controlada")),
        proyeccion=proyectar(ACUMULADO_25_DIAS, 31),
    )
    (r3,) = recomendacion.generar(datos)
    assert r3.mensaje == "Al ritmo actual cerrarías octubre en S/ 4,873.03, S/ 73.03 por encima de tu presupuesto."
    assert (r3.endpoint, r3.argumentos) == ("presupuesto.ver", {"mes": "2026-10"})
    # En un mes que ya terminó no se proyecta el cierre
    assert recomendacion.generar(_datos(mes=date(2026, 9, 1), ejecucion=datos.ejecucion,
                                        proyeccion=datos.proyeccion)) == []


def test_r1_categoria_en_alerta():
    datos = _datos(ejecucion=(_ejecucion(8, "Empaques y envases", "60.00", "50.00", 83.3, "En alerta"),))
    assert _mensajes(datos) == ["Has usado el 83.3 % del presupuesto de Empaques y envases."]


def test_r4_completitud_menor_al_80():
    datos = _datos(completitud=ResumenGastos(cantidad=12, completos=8,
                                             faltantes={"categoría": 1, "descripción": 1, "método de pago": 2}))
    (r4,) = recomendacion.generar(datos)
    assert r4.mensaje == "4 gastos están incompletos; el dato más omitido es método de pago."
    assert r4.argumentos["estado"] == "incompleto"
    singular = _datos(completitud=ResumenGastos(cantidad=2, completos=1, faltantes={"descripción": 1}))
    assert _mensajes(singular) == ["1 gasto está incompleto; el dato más omitido es descripción."]
    assert recomendacion.generar(_datos(completitud=ResumenGastos(cantidad=5, completos=4, faltantes={}))) == []


def test_r5_aumento_mayor_al_30_por_ciento():
    datos = _datos(categorias=(
        _categoria(1, "Insumos y materia prima", "100.00", "60.00"),  # +66.7 %
        _categoria(2, "Mercadería", "45.00", "10.00"),  # menos de S/ 50
        _categoria(5, "Transporte", "60.00", "50.00"),  # +20 %
        _categoria(7, "Mantenimiento", "90.00", "0"),  # sin gasto el mes anterior
        _categoria(None, "Sin categoría", "200.00", "10.00"),
    ))
    assert _mensajes(datos) == ["Tus gastos en Insumos y materia prima subieron 66.7 % respecto al mes pasado."]


def test_r7_categoria_sin_presupuesto_con_mas_del_20_por_ciento():
    datos = _datos(
        ejecucion=(_ejecucion(4, "Alquiler", "900.00", "100.00", 11.1, "Controlada"),),
        categorias=(_categoria(2, "Mercadería", "250.00", participacion=25.0),
                    _categoria(4, "Alquiler", "500.00", participacion=50.0),
                    _categoria(None, "Sin categoría", "250.00", participacion=25.0),
                    _categoria(5, "Transporte", "20.00", participacion=2.0)),
    )
    (r7,) = recomendacion.generar(datos)
    assert r7.mensaje == "Mercadería no tiene presupuesto y representa el 25.0 % de tus gastos."
    assert (r7.accion, r7.endpoint) == ("Definir presupuesto", "presupuesto.ver")


def test_r6_sin_registros_en_los_ultimos_tres_dias():
    assert _mensajes(_datos(ultima_fecha=date(2026, 10, 9))) == [
        "No registras gastos desde el 09/10/2026. ¿Olvidaste anotar alguno?"]
    assert recomendacion.generar(_datos(ultima_fecha=date(2026, 10, 24))) == []
    assert recomendacion.generar(_datos(mes=date(2026, 9, 1), ultima_fecha=date(2026, 9, 9))) == []
    assert recomendacion.generar(_datos(hoy=date(2026, 10, 2), ultima_fecha=None)) == []


def test_rn08_maximo_tres_por_prioridad():
    datos = _datos(
        ejecucion=(
            _ejecucion(8, "Empaques y envases", "60.00", "50.00", 83.3, "En alerta"),
            _ejecucion(4, "Alquiler", "900.00", "900.00", 100.0, "En alerta"),
            _ejecucion(3, "Servicios (luz, agua, gas)", "520.00", "550.30", 105.8, "Excedida"),
        ),
        completitud=ResumenGastos(cantidad=12, completos=8, faltantes={"método de pago": 2}),
        ultima_fecha=date(2026, 10, 9),
    )
    resultado = recomendacion.generar(datos)
    assert len(resultado) == 3
    assert [r.regla for r in resultado] == ["R2", "R1", "R1"]
    assert "Alquiler" in resultado[1].mensaje  # dentro de R1, primero el mayor porcentaje
    assert len(recomendacion.generar(datos, maximo=10)) == 5  # R2, R1, R1, R4 y R6
