"""ReporteService: reporte agrupado en pantalla y su exportación a PDF (RF-19, RF-20; CU-13, CU-14).

El reporte usa el mismo DataFrame de AnaliticaService (una consulta + Pandas,
RNF-01). La pantalla y el PDF se arman con el mismo objeto Reporte, por eso
contienen los mismos datos.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services import analitica
from app.services.calculo import a_soles
from app.services.formato import DIAS_CORTOS, ahora_lima, fecha, fecha_hora, mes_anio, porcentaje, soles
from app.services.periodo import interpretar_mes, texto_mes, ultimo_dia

TIPOS = ("diario", "semanal", "mensual", "personalizado")
AGRUPACIONES = {"categoria": "Categoría", "metodo": "Método de pago", "fecha": "Fecha"}
TIPO_POR_DEFECTO = "mensual"
AGRUPACION_POR_DEFECTO = "categoria"
MENSAJE_SIN_GASTOS = "No hay gastos registrados en este período"
PIE_PDF = "Generado por ControlGastos"


@dataclass(frozen=True)
class SolicitudReporte:
    """Período y agrupación elegidos en P-07."""

    tipo: str
    desde: date
    hasta: date
    agrupacion: str

    @property
    def titulo_periodo(self) -> str:
        if self.tipo == "diario":
            return fecha(self.desde)
        if self.tipo == "semanal":
            return f"Semana del {fecha(self.desde)} al {fecha(self.hasta)}"
        if self.tipo == "mensual":
            return mes_anio(self.desde)
        return f"Del {fecha(self.desde)} al {fecha(self.hasta)}"

    @property
    def nombre_agrupacion(self) -> str:
        return AGRUPACIONES[self.agrupacion]

    def como_argumentos(self) -> dict:
        """Parámetros de la URL que reproducen esta solicitud (pantalla y PDF)."""
        argumentos = {"tipo": self.tipo, "agrupacion": self.agrupacion}
        if self.tipo in ("diario", "semanal"):
            argumentos["fecha"] = self.desde.isoformat()  # en el semanal, el lunes de la semana
        elif self.tipo == "mensual":
            argumentos["mes"] = texto_mes(self.desde)
        else:
            argumentos.update(desde=self.desde.isoformat(), hasta=self.hasta.isoformat())
        return argumentos


def _fecha_de(texto: str | None) -> date | None:
    try:
        return date.fromisoformat((texto or "").strip())
    except ValueError:
        return None


def interpretar_solicitud(argumentos, hoy: date) -> tuple[SolicitudReporte | None, list[str], list[str]]:
    """Lee ?tipo=&agrupacion=&fecha=&mes=&desde=&hasta=. Devuelve (solicitud, avisos, errores)."""
    avisos, errores = [], []
    tipo = argumentos.get("tipo", TIPO_POR_DEFECTO)
    tipo = tipo if tipo in TIPOS else TIPO_POR_DEFECTO
    agrupacion = argumentos.get("agrupacion", AGRUPACION_POR_DEFECTO)
    agrupacion = agrupacion if agrupacion in AGRUPACIONES else AGRUPACION_POR_DEFECTO

    if tipo in ("diario", "semanal"):
        dia = _fecha_de(argumentos.get("fecha")) or hoy
        if tipo == "diario":
            desde = hasta = dia
        else:
            desde = analitica.inicio_de_semana(dia)
            hasta = desde + timedelta(days=6)
    elif tipo == "mensual":
        desde = interpretar_mes(argumentos.get("mes"), hoy)
        hasta = ultimo_dia(desde)
    else:
        desde, hasta = _fecha_de(argumentos.get("desde")), _fecha_de(argumentos.get("hasta"))
        if not desde or not hasta:
            errores.append("Elige la fecha de inicio y la fecha de fin del período personalizado.")
            return None, avisos, errores
        if desde > hasta:
            desde, hasta = hasta, desde
            avisos.append("Intercambiamos las fechas porque «Desde» era posterior a «Hasta».")
    return SolicitudReporte(tipo, desde, hasta, agrupacion), avisos, errores


@dataclass(frozen=True)
class FilaReporte:
    grupo: str
    color: str | None  # punto de color (solo al agrupar por categoría)
    cantidad: int
    total: Decimal  # subtotal del grupo
    porcentaje: float


@dataclass(frozen=True)
class Reporte:
    negocio: str
    solicitud: SolicitudReporte
    filas: tuple
    cantidad: int
    total: Decimal
    emitido: datetime

    @property
    def vacio(self) -> bool:
        return self.cantidad == 0

    @property
    def nombre_archivo(self) -> str:
        """reporte_gastos_AAAAMMDD_AAAAMMDD.pdf"""
        return f"reporte_gastos_{self.solicitud.desde:%Y%m%d}_{self.solicitud.hasta:%Y%m%d}.pdf"


def _filas(df, agrupacion: str) -> tuple:
    if agrupacion == "categoria":
        tabla = analitica.por_categoria(df)
        return tuple(FilaReporte(f.categoria, f.color, int(f.cantidad), a_soles(f.total), f.porcentaje)
                     for f in tabla.itertuples())
    if agrupacion == "metodo":
        tabla = analitica.por_metodo(df)
        return tuple(FilaReporte(f.metodo_pago, None, int(f.cantidad), a_soles(f.total), f.porcentaje)
                     for f in tabla.itertuples())
    tabla = analitica.por_fecha(df)
    return tuple(FilaReporte(f"{DIAS_CORTOS[f.fecha.weekday()]} {fecha(f.fecha)}", None, int(f.cantidad),
                             a_soles(f.total), f.porcentaje)
                 for f in tabla.itertuples())


def generar(usuario, solicitud: SolicitudReporte, emitido: datetime | None = None) -> Reporte:
    """CU-13: reporte del período con subtotales por grupo y total (= suma de los gastos)."""
    df = analitica.construir_dataframe(usuario.id, solicitud.desde, solicitud.hasta)
    return Reporte(
        negocio=usuario.nombre_negocio or usuario.nombre,
        solicitud=solicitud,
        filas=_filas(df, solicitud.agrupacion),
        cantidad=len(df),
        total=analitica.total(df),
        emitido=emitido or ahora_lima(),
    )


# --- PDF A4 con ReportLab (CU-14) -------------------------------------------------------------

_TEXTO = colors.HexColor("#111827")
_SECUNDARIO = colors.HexColor("#6B7280")
_BORDE = colors.HexColor("#E5E7EB")
_FONDO_TOTAL = colors.HexColor("#F3F4F6")

_ESTILO_NEGOCIO = ParagraphStyle("negocio", fontName="Helvetica-Bold", fontSize=11, textColor=_SECUNDARIO, leading=14)
_ESTILO_TITULO = ParagraphStyle("titulo", fontName="Helvetica-Bold", fontSize=20, textColor=_TEXTO, leading=26,
                                spaceAfter=4)
_ESTILO_DATO = ParagraphStyle("dato", fontName="Helvetica", fontSize=10, textColor=_TEXTO, leading=15)
_ESTILO_CELDA = ParagraphStyle("celda", fontName="Helvetica", fontSize=10, textColor=_TEXTO, leading=13)


def _celda_grupo(fila: FilaReporte) -> Paragraph:
    nombre = escape(fila.grupo)
    if fila.color:
        # Punto de color: carácter "l" de ZapfDingbats (círculo lleno)
        nombre = f'<font name="ZapfDingbats" color="{fila.color}">l</font>&nbsp;&nbsp;{nombre}'
    return Paragraph(nombre, _ESTILO_CELDA)


def _tabla_pdf(reporte: Reporte) -> Table:
    encabezado = [reporte.solicitud.nombre_agrupacion, "Cantidad", "Total", "%"]
    datos = [encabezado]
    for fila in reporte.filas:
        datos.append([_celda_grupo(fila), str(fila.cantidad), soles(fila.total), porcentaje(fila.porcentaje)])
    datos.append(["Total", str(reporte.cantidad), soles(reporte.total), porcentaje(100)])
    tabla = Table(datos, colWidths=[92 * mm, 24 * mm, 34 * mm, 24 * mm], repeatRows=1)
    tabla.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (-1, 0), _TEXTO),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 1), (-1, -2), 0.5, _BORDE),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, -1), (-1, -1), _FONDO_TOTAL),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return tabla


def _pie_de_pagina(lienzo, documento) -> None:
    lienzo.saveState()
    lienzo.setFont("Helvetica", 8)
    lienzo.setFillColor(_SECUNDARIO)
    lienzo.drawString(documento.leftMargin, 12 * mm, PIE_PDF)
    lienzo.drawRightString(A4[0] - documento.rightMargin, 12 * mm, f"Página {documento.page}")
    lienzo.restoreState()


def generar_pdf(reporte: Reporte) -> bytes:
    """RF-20: PDF A4 con negocio, título, período, tabla, total, fecha de emisión y pie."""
    buffer = BytesIO()
    solicitud = reporte.solicitud
    documento = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title=f"Reporte de gastos - {solicitud.titulo_periodo}",
        author=reporte.negocio,
        creator="ControlGastos",
    )
    elementos = [
        Paragraph(escape(reporte.negocio), _ESTILO_NEGOCIO),
        Paragraph("Reporte de gastos", _ESTILO_TITULO),
        Paragraph(f"<b>Período:</b> {escape(solicitud.titulo_periodo)}", _ESTILO_DATO),
        Paragraph(f"<b>Agrupado por:</b> {escape(solicitud.nombre_agrupacion.lower())}", _ESTILO_DATO),
        Paragraph(f"<b>Fecha de emisión:</b> {fecha_hora(reporte.emitido)}", _ESTILO_DATO),
        Spacer(1, 8 * mm),
    ]
    if reporte.vacio:
        elementos.append(Paragraph(MENSAJE_SIN_GASTOS + ".", _ESTILO_DATO))
    else:
        elementos.append(_tabla_pdf(reporte))
        elementos.append(Spacer(1, 4 * mm))
        gastos = "1 gasto" if reporte.cantidad == 1 else f"{reporte.cantidad} gastos"
        elementos.append(Paragraph(f"<b>Total del período:</b> {soles(reporte.total)} ({gastos})", _ESTILO_DATO))
    documento.build(elementos, onFirstPage=_pie_de_pagina, onLaterPages=_pie_de_pagina)
    return buffer.getvalue()
