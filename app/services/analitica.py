"""AnaliticaService: un DataFrame por consulta y las métricas A1–A9 y S1 (RF-15, RF-16).

Las métricas son funciones puras sobre el DataFrame (se prueban sin base de
datos); solo `construir_dataframe` y `presupuestos_del_mes` consultan PostgreSQL.
Dashboard, listado y reportes comparten la misma fuente: A8 coincide con
GastoService y A7/A9 con PresupuestoService.
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

import pandas as pd
from sqlalchemy import select

from app.extensions import db
from app.models import Categoria, Gasto, MetodoPago, Presupuesto
from app.models.presupuesto import estado_presupuesto
from app.services import proyeccion as proyeccion_service
from app.services import recomendacion as recomendacion_service
from app.services.calculo import a_soles, porcentaje_de
from app.services.formato import DIAS_CORTOS, MESES_CORTOS
from app.services.gasto import ResumenGastos
from app.services.periodo import mes_anterior, texto_mes, ultimo_dia
from app.services.proyeccion import Proyeccion

SIN_CATEGORIA = "Sin categoría"
SIN_METODO = "Sin registrar"
COLOR_SIN_CATEGORIA = "#D1D5DB"
# Gráfico de método de pago (sección 11.5): una sola serie; "Sin registrar" en gris claro
COLOR_METODO = "#111827"
COLOR_METODO_SIN_REGISTRAR = "#D1D5DB"
# Nombres cortos en el gráfico (como los botones de P-03)
NOMBRES_CORTOS_METODO = {"Transferencia bancaria": "Transferencia"}
ESCALA_BARRA = 125
MESES_EVOLUCION = 6
COLUMNAS = (
    "id", "fecha", "monto", "categoria_id", "categoria", "color",
    "metodo_pago_id", "metodo_pago", "descripcion",
)
CERO = Decimal("0.00")


# --- Construcción del DataFrame ----------------------------------------------------------

def normalizar(filas) -> pd.DataFrame:
    """Arma el DataFrame y completa los vacíos: "Sin categoría" y "Sin registrar"."""
    df = pd.DataFrame(list(filas), columns=list(COLUMNAS))
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["monto"] = df["monto"].astype(float)
    df["categoria"] = df["categoria"].fillna(SIN_CATEGORIA)
    df["color"] = df["color"].fillna(COLOR_SIN_CATEGORIA)
    df["metodo_pago"] = df["metodo_pago"].fillna(SIN_METODO)
    return df


def construir_dataframe(usuario_id: int, desde: date, hasta: date) -> pd.DataFrame:
    """Gastos vigentes del usuario entre dos fechas, unidos con categoría y método, en una consulta."""
    consulta = (
        select(
            Gasto.id, Gasto.fecha, Gasto.monto, Gasto.categoria_id, Categoria.nombre, Categoria.color,
            Gasto.metodo_pago_id, MetodoPago.nombre, Gasto.descripcion,
        )
        .outerjoin(Categoria, Categoria.id == Gasto.categoria_id)
        .outerjoin(MetodoPago, MetodoPago.id == Gasto.metodo_pago_id)
        .where(Gasto.usuario_id == usuario_id, Gasto.eliminado.is_(False), Gasto.fecha.between(desde, hasta))
        .order_by(Gasto.fecha, Gasto.id)
    )
    return normalizar(db.session.execute(consulta).all())


def presupuestos_del_mes(usuario_id: int, mes: date) -> pd.DataFrame:
    """Presupuesto de cada categoría en el mes (para A7 y A9)."""
    consulta = (
        select(Presupuesto.categoria_id, Categoria.nombre, Categoria.color, Presupuesto.monto)
        .join(Categoria, Categoria.id == Presupuesto.categoria_id)
        .where(Presupuesto.usuario_id == usuario_id, Presupuesto.anio == mes.year, Presupuesto.mes == mes.month)
        .order_by(Categoria.id)
    )
    df = pd.DataFrame(db.session.execute(consulta).all(), columns=["categoria_id", "categoria", "color", "planificado"])
    df["planificado"] = df["planificado"].astype(float)
    return df


def del_periodo(df: pd.DataFrame, desde: date, hasta: date) -> pd.DataFrame:
    return df[(df["fecha"] >= pd.Timestamp(desde)) & (df["fecha"] <= pd.Timestamp(hasta))]


# --- A1 a A9 -------------------------------------------------------------------------------

def total(df: pd.DataFrame) -> Decimal:
    """A1: total gastado del período."""
    return a_soles(df["monto"].sum())


def variacion_porcentual(actual: Decimal, anterior: Decimal) -> float | None:
    """A2: (actual − anterior) / anterior × 100; sin variación si el anterior es cero."""
    return porcentaje_de(actual - anterior, anterior)


def por_categoria(df: pd.DataFrame) -> pd.DataFrame:
    """A3: cantidad, total y % por categoría (la suma de los totales es A1)."""
    columnas = ["categoria_id", "categoria", "color", "cantidad", "total", "porcentaje"]
    if df.empty:
        return pd.DataFrame(columns=columnas)
    agrupado = (
        df.groupby("categoria_id", dropna=False, sort=False)
        .agg(categoria=("categoria", "first"), color=("color", "first"),
             cantidad=("monto", "size"), total=("monto", "sum"))
        .reset_index()
    )
    total_general = df["monto"].sum()
    agrupado["porcentaje"] = [porcentaje_de(round(valor, 2), round(total_general, 2)) for valor in agrupado["total"]]
    agrupado["total"] = agrupado["total"].round(2)
    return agrupado.sort_values(["total", "categoria"], ascending=[False, True], ignore_index=True)[columnas]


def por_metodo(df: pd.DataFrame) -> pd.DataFrame:
    """A4: total por método de pago, con "Sin registrar"."""
    columnas = ["metodo_pago_id", "metodo_pago", "cantidad", "total", "porcentaje"]
    if df.empty:
        return pd.DataFrame(columns=columnas)
    agrupado = (
        df.groupby("metodo_pago_id", dropna=False, sort=False)
        .agg(metodo_pago=("metodo_pago", "first"), cantidad=("monto", "size"), total=("monto", "sum"))
        .reset_index()
    )
    total_general = df["monto"].sum()
    agrupado["porcentaje"] = [porcentaje_de(round(valor, 2), round(total_general, 2)) for valor in agrupado["total"]]
    agrupado["total"] = agrupado["total"].round(2)
    return agrupado.sort_values(["total", "metodo_pago"], ascending=[False, True], ignore_index=True)[columnas]


def por_fecha(df: pd.DataFrame) -> pd.DataFrame:
    """Cantidad, total y % por día con gastos, del más antiguo al más reciente (reportes)."""
    columnas = ["fecha", "cantidad", "total", "porcentaje"]
    if df.empty:
        return pd.DataFrame(columns=columnas)
    agrupado = (
        df.groupby(df["fecha"].dt.date)
        .agg(cantidad=("monto", "size"), total=("monto", "sum"))
        .rename_axis("fecha")
        .reset_index()
    )
    total_general = df["monto"].sum()
    agrupado["porcentaje"] = [porcentaje_de(round(valor, 2), round(total_general, 2)) for valor in agrupado["total"]]
    agrupado["total"] = agrupado["total"].round(2)
    return agrupado.sort_values("fecha", ignore_index=True)[columnas]


def evolucion_diaria(df: pd.DataFrame, desde: date, hasta: date) -> pd.DataFrame:
    """A5: total por día con relleno en cero y su acumulado."""
    dias = pd.date_range(desde, hasta, freq="D")
    serie = df.set_index("fecha")["monto"].resample("D").sum() if not df.empty else pd.Series(dtype=float)
    serie = serie.reindex(dias, fill_value=0.0)
    resultado = pd.DataFrame({"fecha": dias, "total": serie.to_numpy(dtype=float)})
    resultado["acumulado"] = resultado["total"].cumsum().round(2)
    resultado["total"] = resultado["total"].round(2)
    return resultado


def evolucion_mensual(df: pd.DataFrame, mes_final: date, meses: int = MESES_EVOLUCION) -> pd.DataFrame:
    """A6: total de cada uno de los últimos `meses` meses (incluido mes_final)."""
    inicios = pd.date_range(end=pd.Timestamp(mes_final.replace(day=1)), periods=meses, freq="MS")
    serie = df.set_index("fecha")["monto"].resample("MS").sum() if not df.empty else pd.Series(dtype=float)
    serie = serie.reindex(inicios, fill_value=0.0)
    return pd.DataFrame({"mes": inicios, "total": serie.to_numpy(dtype=float).round(2)})


def ejecucion_presupuestaria(df: pd.DataFrame, presupuestos: pd.DataFrame) -> pd.DataFrame:
    """A7: ejecutado / planificado × 100 por categoría con presupuesto y su estado (RN-05, RN-06)."""
    resultado = presupuestos.copy()
    ejecutado = df.groupby("categoria_id")["monto"].sum() if not df.empty else pd.Series(dtype=float)
    resultado["ejecutado"] = resultado["categoria_id"].map(ejecutado).fillna(0.0).astype(float).round(2)
    # dtype object: conserva None (presupuesto en cero) en lugar de convertirlo en NaN
    resultado["porcentaje"] = pd.Series(
        [porcentaje_de(e, p) for e, p in zip(resultado["ejecutado"], resultado["planificado"])],
        index=resultado.index, dtype=object,
    )
    resultado["estado"] = [
        estado_presupuesto(a_soles(e), a_soles(p)) for e, p in zip(resultado["ejecutado"], resultado["planificado"])
    ]
    return resultado


def completitud(df: pd.DataFrame) -> ResumenGastos:
    """A8: registros con los cinco campos / total × 100 y el campo con más omisiones (RN-01)."""
    if df.empty:
        return ResumenGastos()
    faltantes = {
        "categoría": df["categoria_id"].isna(),
        "descripción": df["descripcion"].fillna("").astype(str).str.strip() == "",
        "método de pago": df["metodo_pago_id"].isna(),
    }
    incompletos = faltantes["categoría"] | faltantes["descripción"] | faltantes["método de pago"]
    return ResumenGastos(
        cantidad=len(df),
        total=total(df),
        completos=int((~incompletos).sum()),
        faltantes={campo: int(serie.sum()) for campo, serie in faltantes.items()},
    )


def presupuesto_usado(ejecucion: pd.DataFrame) -> float | None:
    """A9: Σ ejecutado / Σ planificado × 100 (solo categorías con presupuesto)."""
    if ejecucion.empty:
        return None
    ejecutado = sum((a_soles(valor) for valor in ejecucion["ejecutado"]), CERO)
    planificado = sum((a_soles(valor) for valor in ejecucion["planificado"]), CERO)
    return porcentaje_de(ejecutado, planificado)


# --- S1: gasto semanal apilado ----------------------------------------------------------------

def inicio_de_semana(fecha_dia: date) -> date:
    """Lunes de la semana de la fecha."""
    return fecha_dia - timedelta(days=fecha_dia.weekday())


@dataclass(frozen=True)
class SemanaApilada:
    lunes: date
    etiquetas: tuple  # "lun 5", "mar 6", …
    series: tuple  # {"categoria_id", "categoria", "color", "valores" (7), "total"} por categoría
    total: float


def semana_apilada(df: pd.DataFrame, lunes: date) -> SemanaApilada:
    """S1: gasto por día (lun–dom) y por categoría, con el total por categoría y el general."""
    dias = pd.date_range(lunes, periods=7, freq="D")
    semana = df[(df["fecha"] >= dias[0]) & (df["fecha"] <= dias[-1])]
    series = []
    for categoria_id, grupo in semana.groupby("categoria_id", dropna=False, sort=False):
        por_dia = grupo.groupby("fecha")["monto"].sum().reindex(dias, fill_value=0.0)
        series.append({
            "categoria_id": None if pd.isna(categoria_id) else int(categoria_id),
            "categoria": grupo["categoria"].iloc[0],
            "color": grupo["color"].iloc[0],
            "valores": [round(float(valor), 2) for valor in por_dia],
            "total": round(float(grupo["monto"].sum()), 2),
        })
    series.sort(key=lambda serie: (-serie["total"], serie["categoria"]))
    etiquetas = tuple(f"{DIAS_CORTOS[indice]} {dia.day}" for indice, dia in enumerate(dias))
    return SemanaApilada(lunes, etiquetas, tuple(series), round(float(semana["monto"].sum()), 2))


# --- Análisis completo del mes (dashboard) ------------------------------------------------------

def corte_del_mes(mes: date, hoy: date) -> date | None:
    """Último día que cuenta: hoy en el mes en curso, fin de mes si ya pasó; None si es futuro."""
    mes = mes.replace(day=1)
    if mes > hoy.replace(day=1):
        return None
    return hoy if (mes.year, mes.month) == (hoy.year, hoy.month) else ultimo_dia(mes)


def misma_fecha_mes_anterior(mes: date, corte: date) -> tuple[date, date]:
    """Del 1 del mes anterior hasta el mismo día del corte (o hasta su último día)."""
    previo = mes_anterior(mes)
    if corte == ultimo_dia(mes):
        return previo, ultimo_dia(previo)
    return previo, previo.replace(day=min(corte.day, ultimo_dia(previo).day))


@dataclass(frozen=True)
class AnalisisMes:
    mes: date
    corte: date | None
    gastos: pd.DataFrame  # gastos del mes
    total: Decimal  # A1
    total_anterior: Decimal  # mes anterior a la misma fecha
    variacion: float | None  # A2
    por_categoria: pd.DataFrame  # A3
    por_metodo: pd.DataFrame  # A4
    diaria: pd.DataFrame  # A5 (todos los días del mes)
    mensual: pd.DataFrame  # A6
    ejecucion: pd.DataFrame  # A7
    completitud: ResumenGastos  # A8
    presupuesto_usado: float | None  # A9
    total_planificado: Decimal
    proyeccion: Proyeccion  # P1
    recomendaciones: list  # R1–R7

    @property
    def sin_gastos(self) -> bool:
        return self.gastos.empty

    @property
    def tiene_presupuesto(self) -> bool:
        return not self.ejecucion.empty

    @property
    def total_ejecutado_presupuestado(self) -> Decimal:
        return sum((a_soles(valor) for valor in self.ejecucion["ejecutado"]), CERO)

    @property
    def estado_presupuesto(self) -> str | None:
        """Estado del presupuesto total del mes (barra del KPI "Presupuesto usado")."""
        if not self.tiene_presupuesto:
            return None
        return estado_presupuesto(self.total_ejecutado_presupuestado, self.total_planificado)

    @property
    def porcentaje_barra(self) -> float:
        if self.presupuesto_usado is None:
            return float(ESCALA_BARRA) if self.total_ejecutado_presupuestado > 0 else 0.0
        return min(self.presupuesto_usado, float(ESCALA_BARRA))

    def mayor_ejecucion(self, cantidad: int = 5) -> list[dict]:
        """Las categorías con mayor % de ejecución (tarjeta "Presupuesto por categoría")."""
        filas = []
        for fila in self.ejecucion.itertuples():
            if fila.porcentaje is not None:
                barra = min(fila.porcentaje, float(ESCALA_BARRA))
            else:  # presupuesto en cero
                barra = float(ESCALA_BARRA) if fila.ejecutado > 0 else 0.0
            filas.append({
                "categoria_id": int(fila.categoria_id), "categoria": fila.categoria, "color": fila.color,
                "planificado": a_soles(fila.planificado), "ejecutado": a_soles(fila.ejecutado),
                "porcentaje": fila.porcentaje, "estado": fila.estado, "porcentaje_barra": barra,
            })
        filas.sort(key=lambda fila: (-fila["porcentaje_barra"], fila["categoria"]))
        return filas[:cantidad]


def _proyeccion(gastos_mes: pd.DataFrame, diaria: pd.DataFrame, mes: date, hoy: date) -> Proyeccion:
    ultimo_con_datos = gastos_mes["fecha"].max().date() if not gastos_mes.empty else None
    corte = proyeccion_service.dia_de_corte(mes, hoy, ultimo_con_datos)
    if corte is None:
        return Proyeccion(suficiente=False)
    return proyeccion_service.proyectar_mes(
        diaria["acumulado"].iloc[:corte].tolist(),
        dias_con_registros=gastos_mes["fecha"].nunique(),
        registros=len(gastos_mes),
        dias_mes=ultimo_dia(mes).day,
    )


def _datos_de_recomendacion(mes, hoy, gastos_mes, gastos_previos, categorias, ejecucion, completitud_mes, proyeccion):
    anteriores = (
        gastos_previos.groupby("categoria_id")["monto"].sum() if not gastos_previos.empty else pd.Series(dtype=float)
    )
    return recomendacion_service.DatosRecomendacion(
        mes=mes,
        hoy=hoy,
        ejecucion=tuple(
            recomendacion_service.EjecucionCategoria(
                int(fila.categoria_id), fila.categoria, a_soles(fila.planificado), a_soles(fila.ejecutado),
                fila.porcentaje, fila.estado,
            )
            for fila in ejecucion.itertuples()
        ),
        categorias=tuple(
            recomendacion_service.GastoCategoria(
                None if pd.isna(fila.categoria_id) else int(fila.categoria_id),
                fila.categoria,
                a_soles(fila.total),
                a_soles(anteriores.get(fila.categoria_id, 0.0)) if not pd.isna(fila.categoria_id) else Decimal("0.00"),
                fila.porcentaje,
            )
            for fila in categorias.itertuples()
        ),
        completitud=completitud_mes,
        proyeccion=proyeccion,
        ultima_fecha=gastos_mes["fecha"].max().date() if not gastos_mes.empty else None,
    )


def _titulo_semana(lunes: date) -> str:
    """'26 oct – 1 nov'."""
    domingo = lunes + timedelta(days=6)
    return (f"{lunes.day} {MESES_CORTOS[lunes.month - 1]} – "
            f"{domingo.day} {MESES_CORTOS[domingo.month - 1]}")


def datos_graficos(analisis: "AnalisisMes", semana: SemanaApilada, hoy: date) -> dict:
    """JSON de /api/dashboard para Chart.js: S1, A5 con P1 y presupuesto, y A4 (RF-15, RF-16)."""
    corte = analisis.corte.day if analisis.corte else 0
    real = [round(float(valor), 2) if indice < corte else None
            for indice, valor in enumerate(analisis.diaria["acumulado"])]
    proyeccion = [None] * len(analisis.diaria)
    for dia, valor in analisis.proyeccion.linea():
        proyeccion[dia - 1] = valor
    siguiente = semana.lunes + timedelta(days=7)
    metodos = analisis.por_metodo
    return {
        "mes": texto_mes(analisis.mes),
        "semana": {
            "lunes": semana.lunes.isoformat(),
            "titulo": _titulo_semana(semana.lunes),
            "anterior": (semana.lunes - timedelta(days=7)).isoformat(),
            "siguiente": siguiente.isoformat() if siguiente <= hoy else None,
            "etiquetas": list(semana.etiquetas),
            "series": [
                {"categoria": serie["categoria"], "color": serie["color"],
                 "valores": serie["valores"], "total": serie["total"]}
                for serie in semana.series
            ],
            "total": semana.total,
        },
        "acumulado": {
            "etiquetas": [str(dia) for dia in range(1, len(analisis.diaria) + 1)],
            "real": real,
            "proyeccion": proyeccion,
            "presupuesto": float(analisis.total_planificado) if analisis.tiene_presupuesto else None,
            "mensaje_proyeccion": analisis.proyeccion.mensaje,
        },
        "metodos": {
            "etiquetas": [NOMBRES_CORTOS_METODO.get(nombre, nombre) for nombre in metodos["metodo_pago"]],
            "valores": [round(float(valor), 2) for valor in metodos["total"]],
            "colores": [COLOR_METODO_SIN_REGISTRAR if nombre == SIN_METODO else COLOR_METODO
                        for nombre in metodos["metodo_pago"]],
        },
    }


def analizar_mes(usuario_id: int, mes: date, hoy: date) -> AnalisisMes:
    """Todas las métricas del mes con dos consultas: seis meses de gastos y el presupuesto del mes."""
    mes = mes.replace(day=1)
    fin_mes = ultimo_dia(mes)
    inicio_ventana = mes
    for _ in range(MESES_EVOLUCION - 1):
        inicio_ventana = mes_anterior(inicio_ventana)
    ventana = construir_dataframe(usuario_id, inicio_ventana, fin_mes)
    presupuestos = presupuestos_del_mes(usuario_id, mes)

    gastos_mes = del_periodo(ventana, mes, fin_mes)
    corte = corte_del_mes(mes, hoy)
    gastos_previos = del_periodo(ventana, *misma_fecha_mes_anterior(mes, corte)) if corte else ventana.iloc[0:0]

    total_mes, total_anterior = total(gastos_mes), total(gastos_previos)
    categorias = por_categoria(gastos_mes)
    ejecucion = ejecucion_presupuestaria(gastos_mes, presupuestos)
    diaria = evolucion_diaria(gastos_mes, mes, fin_mes)
    completitud_mes = completitud(gastos_mes)
    proyeccion = _proyeccion(gastos_mes, diaria, mes, hoy)
    datos = _datos_de_recomendacion(
        mes, hoy, gastos_mes, gastos_previos, categorias, ejecucion, completitud_mes, proyeccion
    )
    return AnalisisMes(
        mes=mes,
        corte=corte,
        gastos=gastos_mes,
        total=total_mes,
        total_anterior=total_anterior,
        variacion=variacion_porcentual(total_mes, total_anterior),
        por_categoria=categorias,
        por_metodo=por_metodo(gastos_mes),
        diaria=diaria,
        mensual=evolucion_mensual(ventana, mes),
        ejecucion=ejecucion,
        completitud=completitud_mes,
        presupuesto_usado=presupuesto_usado(ejecucion),
        total_planificado=sum((a_soles(valor) for valor in ejecucion["planificado"]), CERO),
        proyeccion=proyeccion,
        recomendaciones=recomendacion_service.generar(datos),
    )
