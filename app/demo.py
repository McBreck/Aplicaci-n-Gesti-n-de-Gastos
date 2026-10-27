"""Datos de demostración PRUEBA: `flask demo crear` y `flask demo borrar`.

La cuenta "PRUEBA Panadería" recibe 60 días de gastos de una panadería (algunos
incompletos) y el presupuesto de cada mes. Los montos salen de una semilla fija:
con la misma fecha se generan siempre los mismos datos. Los datos PRUEBA nunca
se presentan como resultados de la investigación.
"""
import random
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import and_, delete, or_, select

from app.extensions import db
from app.models import Auditoria, Categoria, Gasto, MetodoPago, Presupuesto, Usuario
from app.models.usuario import ROL_MICROEMPRENDEDOR
from app.services import auditoria
from app.services import usuario as usuario_service
from app.services.periodo import mes_siguiente
from app.services.presupuesto import periodo_editable

PREFIJO = "PRUEBA"
NOMBRE = "PRUEBA Panadería"
CORREO = "prueba.panaderia@controlgastos.test"
RUBRO = "Panadería"
DIAS = 60
SEMILLA = 2026
PROBABILIDAD_INCOMPLETO = 0.2
# Campo que falta en un gasto incompleto y su peso: el método de pago es el más omitido (A8)
CAMPOS_OMITIDOS = (("metodo", 3), ("descripcion", 1), ("categoria", 1))
CENTIMO = Decimal("0.01")


class ErrorDemo(Exception):
    """Error con un mensaje listo para mostrar en la consola."""


@dataclass(frozen=True)
class Habito:
    """Gasto que se repite: cada día con cierta probabilidad, un día de la semana o un día del mes."""

    categoria: str
    opciones: tuple[tuple[str, int, int], ...]  # (descripción, monto mínimo, monto máximo)
    metodos: tuple[str, ...]
    probabilidad: float = 1.0
    dia_semana: int | None = None  # 0 = lunes
    dia_mes: int | None = None

    def ocurre(self, dia: date, azar: random.Random) -> bool:
        if self.dia_mes is not None:
            return dia.day == self.dia_mes
        if self.dia_semana is not None:
            return dia.weekday() == self.dia_semana
        return azar.random() < self.probabilidad


HABITOS = (
    Habito("Insumos y materia prima", (
        ("Harina 50 kg", 120, 150), ("Azúcar rubia 25 kg", 75, 90), ("Mantequilla 5 kg", 80, 100),
        ("Huevos (1 jaba)", 14, 18), ("Levadura fresca", 8, 15), ("Leche evaporada (1 caja)", 95, 110),
    ), ("Efectivo", "Yape", "Plin", "Tarjeta"), probabilidad=0.85),
    Habito("Transporte", (
        ("Mototaxi al mercado", 4, 8), ("Flete de insumos", 15, 25), ("Pasaje en combi", 2, 4),
    ), ("Efectivo", "Yape"), probabilidad=0.45),
    Habito("Servicios (luz, agua, gas)", (("Balón de gas 10 kg", 48, 56),), ("Efectivo",), probabilidad=0.1),
    Habito("Mantenimiento", (
        ("Repuesto de la batidora", 60, 180), ("Arreglo de la vitrina", 50, 120),
    ), ("Efectivo", "Tarjeta"), probabilidad=0.03),
    Habito("Otros", (
        ("Útiles de limpieza", 10, 35), ("Bolsas de basura", 5, 12), ("Recarga del celular del negocio", 10, 20),
    ), ("Efectivo", "Plin"), probabilidad=0.06),
    Habito("Mercadería", (("Gaseosas y jugos para reventa", 80, 140),), ("Yape", "Efectivo"), dia_semana=0),
    Habito("Empaques y envases", (
        ("Bolsas de papel", 20, 35), ("Cajas para tortas", 30, 60),
    ), ("Efectivo",), dia_semana=3),
    Habito("Sueldos y pagos a terceros", (("Pago semanal al ayudante", 350, 350),), ("Efectivo",), dia_semana=5),
    Habito("Alquiler", (("Alquiler del local", 900, 900),), ("Transferencia bancaria",), dia_mes=1),
    Habito("Servicios (luz, agua, gas)", (("Recibo de luz", 180, 260),), ("Transferencia bancaria",), dia_mes=12),
    Habito("Servicios (luz, agua, gas)", (("Recibo de agua", 60, 90),), ("Yape",), dia_mes=15),
    Habito("Mantenimiento", (("Mantenimiento del horno", 40, 80),), ("Efectivo",), dia_mes=20),
)

# Presupuesto de cada mes; "Otros" queda sin presupuesto. Algunos montos quedan justos
# a propósito, para que se vean las alertas y las recomendaciones (RF-14, RF-18).
PRESUPUESTO_MENSUAL = {
    "Insumos y materia prima": Decimal("1800.00"),
    "Mercadería": Decimal("450.00"),
    "Servicios (luz, agua, gas)": Decimal("480.00"),
    "Alquiler": Decimal("900.00"),
    "Transporte": Decimal("90.00"),
    "Sueldos y pagos a terceros": Decimal("1500.00"),
    "Mantenimiento": Decimal("150.00"),
    "Empaques y envases": Decimal("200.00"),
}


@dataclass(frozen=True)
class GastoDemo:
    fecha: date
    monto: Decimal
    categoria: str | None
    descripcion: str | None
    metodo: str | None


def _monto(minimo: int, maximo: int, azar: random.Random) -> Decimal:
    """Monto entre los límites, en múltiplos de S/ 0.50."""
    return (Decimal(azar.randint(minimo * 2, maximo * 2)) / 2).quantize(CENTIMO)


def planificar_gastos(hoy: date) -> list[GastoDemo]:
    """Gastos de los últimos 60 días hasta hoy (nunca futuros, RN-04), del más antiguo al más reciente."""
    azar = random.Random(SEMILLA)
    campos, pesos = zip(*CAMPOS_OMITIDOS)
    gastos = []
    for atras in range(DIAS - 1, -1, -1):
        dia = hoy - timedelta(days=atras)
        for habito in HABITOS:
            if not habito.ocurre(dia, azar):
                continue
            descripcion, minimo, maximo = azar.choice(habito.opciones)
            datos = {"categoria": habito.categoria, "descripcion": descripcion, "metodo": azar.choice(habito.metodos)}
            if azar.random() < PROBABILIDAD_INCOMPLETO:
                datos[azar.choices(campos, weights=pesos)[0]] = None
            gastos.append(GastoDemo(fecha=dia, monto=_monto(minimo, maximo, azar), **datos))
    return gastos


def meses_del_periodo(hoy: date) -> list[date]:
    """Primer día de cada mes que toca el período de 60 días."""
    mes = (hoy - timedelta(days=DIAS - 1)).replace(day=1)
    meses = []
    while mes <= hoy:
        meses.append(mes)
        mes = mes_siguiente(mes)
    return meses


def meses_con_presupuesto(hoy: date) -> list[date]:
    """Meses del período en los que se puede definir presupuesto (desde enero de 2026)."""
    return [mes for mes in meses_del_periodo(hoy) if periodo_editable(mes)]


@dataclass(frozen=True)
class ResumenDemo:
    correo: str
    gastos: int
    incompletos: int
    presupuestos: int
    meses: tuple
    desde: date
    hasta: date


def crear(contrasena: str, hoy: date) -> ResumenDemo:
    """`flask demo crear`: la cuenta PRUEBA Panadería con sus gastos y presupuestos, en una sola transacción."""
    if usuario_service.existe_correo(CORREO):
        raise ErrorDemo("La cuenta de demostración ya existe. Bórrala con «flask demo borrar» y vuelve a crearla.")
    usuario_service.validar_contrasena(contrasena)

    usuario = Usuario(rol=ROL_MICROEMPRENDEDOR, nombre=NOMBRE, correo=CORREO, nombre_negocio=NOMBRE, rubro=RUBRO)
    usuario.establecer_contrasena(contrasena)
    db.session.add(usuario)
    db.session.flush()
    usuario_service.copiar_categorias_predeterminadas(usuario)
    db.session.flush()
    categorias = dict(db.session.execute(
        select(Categoria.nombre, Categoria.id).where(Categoria.usuario_id == usuario.id)
    ).all())
    metodos = dict(db.session.execute(select(MetodoPago.nombre, MetodoPago.id)).all())

    gastos = [
        Gasto(
            usuario_id=usuario.id, fecha=gasto.fecha, monto=gasto.monto, descripcion=gasto.descripcion,
            categoria_id=categorias.get(gasto.categoria), metodo_pago_id=metodos.get(gasto.metodo),
        )
        for gasto in planificar_gastos(hoy)
    ]
    db.session.add_all(gastos)
    incompletos = sum(1 for gasto in gastos if not gasto.evaluar_completitud())

    meses = meses_con_presupuesto(hoy)
    presupuestos = [
        Presupuesto(usuario_id=usuario.id, categoria_id=categorias[nombre], anio=mes.year, mes=mes.month, monto=monto)
        for mes in meses
        for nombre, monto in PRESUPUESTO_MENSUAL.items()
        if nombre in categorias
    ]
    db.session.add_all(presupuestos)
    auditoria.registrar(
        auditoria.CREAR, usuario_service.ENTIDAD, entidad_id=usuario.id,
        detalle={"nuevo": {"nombre": NOMBRE, "correo": CORREO}, "origen": "flask demo crear"},
    )
    db.session.commit()
    return ResumenDemo(
        correo=CORREO, gastos=len(gastos), incompletos=incompletos, presupuestos=len(presupuestos),
        meses=tuple(meses), desde=hoy - timedelta(days=DIAS - 1), hasta=hoy,
    )


def cuentas_prueba() -> list[Usuario]:
    """Cuentas cuyo nombre empieza con PRUEBA (datos de prueba)."""
    return list(db.session.scalars(select(Usuario).where(Usuario.nombre.startswith(PREFIJO)).order_by(Usuario.id)))


@dataclass(frozen=True)
class ResumenBorrado:
    cuentas: int = 0
    gastos: int = 0
    presupuestos: int = 0
    categorias: int = 0
    eventos: int = 0


def borrar() -> ResumenBorrado:
    """`flask demo borrar`: elimina las cuentas PRUEBA con sus gastos, presupuestos, categorías y bitácora."""
    ids = [cuenta.id for cuenta in cuentas_prueba()]
    if not ids:
        return ResumenBorrado()
    # Primero lo que apunta a las categorías y a las cuentas (claves foráneas)
    gastos = db.session.execute(delete(Gasto).where(Gasto.usuario_id.in_(ids))).rowcount
    presupuestos = db.session.execute(delete(Presupuesto).where(Presupuesto.usuario_id.in_(ids))).rowcount
    eventos = db.session.execute(delete(Auditoria).where(or_(
        Auditoria.usuario_id.in_(ids),
        and_(Auditoria.entidad == usuario_service.ENTIDAD, Auditoria.entidad_id.in_(ids)),
    ))).rowcount
    categorias = db.session.execute(delete(Categoria).where(Categoria.usuario_id.in_(ids))).rowcount
    cuentas = db.session.execute(delete(Usuario).where(Usuario.id.in_(ids))).rowcount
    db.session.commit()
    return ResumenBorrado(cuentas, gastos, presupuestos, categorias, eventos)
