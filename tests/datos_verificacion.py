"""Datos de verificación de la sección 9 de la especificación (ficticios).

Se usan en las pruebas de completitud (EDT 3.3) y de analítica (EDT 3.5).
Nunca se presentan como resultados de la investigación.
"""

# (fecha, monto, categoría, descripción, método de pago); None = campo vacío
GASTOS_OCTUBRE_2026 = (
    ("2026-10-01", "190.00", "Insumos y materia prima", "Harina 2 sacos", "Efectivo"),
    ("2026-10-01", "24.00", "Insumos y materia prima", None, "Efectivo"),
    ("2026-10-02", "58.00", "Servicios (luz, agua, gas)", "Balón de gas 10 kg", None),
    ("2026-10-03", "15.00", "Empaques y envases", "Bolsas kraft x 100", "Yape"),
    ("2026-10-04", "900.00", "Alquiler", "Alquiler del local", "Transferencia bancaria"),
    ("2026-10-05", "86.50", "Insumos y materia prima", "Mantequilla 5 kg", "Yape"),
    ("2026-10-05", "6.00", "Transporte", "Pasaje al mercado", "Efectivo"),
    ("2026-10-06", "212.30", "Servicios (luz, agua, gas)", "Recibo de luz", "Transferencia bancaria"),
    ("2026-10-07", "42.00", None, "Azúcar 1 saco", "Efectivo"),
    ("2026-10-08", "18.00", "Insumos y materia prima", "Huevos 1 jaba", "Plin"),
    ("2026-10-08", "35.00", "Empaques y envases", "Cajas para tortas", "Yape"),
    ("2026-10-09", "280.00", "Servicios (luz, agua, gas)", "Recibo de agua y gas", None),
)

TOTAL_OCTUBRE_2026 = "1866.80"
COMPLETITUD_OCTUBRE_2026 = 66.7  # 8 de 12
CAMPO_MAS_OMITIDO_OCTUBRE_2026 = "método de pago"  # 2 omisiones

PRESUPUESTO_OCTUBRE_2026 = {
    "Insumos y materia prima": "400.00",
    "Servicios (luz, agua, gas)": "520.00",
    "Empaques y envases": "60.00",
    "Alquiler": "900.00",
    "Transporte": "50.00",
}

# Proyección P1: acumulado diario de 25 días en un mes de 31 días
ACUMULADO_25_DIAS = (
    219.64, 329.47, 480.47, 604.02, 741.3, 1070.76, 1166.86, 1304.13, 1427.68, 1592.42,
    1702.24, 1853.24, 1949.34, 2306.26, 2429.81, 2567.08, 2676.91, 2827.91, 2951.46, 3088.74,
    3390.75, 3500.57, 3637.85, 3761.4, 3912.4,
)
