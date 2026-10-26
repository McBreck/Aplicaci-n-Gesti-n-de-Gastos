# 04 — Analítica de datos

> Fuente: prompt maestro de implementación, sección 9 (EDT 2.4).

## 9. Analítica de datos (aprobada en EDT 2.4)

Todos los análisis parten de **un mismo DataFrame** construido por `AnaliticaService` con una consulta parametrizada: gastos del usuario autenticado, del período, `eliminado = FALSE`, unidos con categoría (nombre, color) y método de pago. Vacíos: categoría → "Sin categoría", método → "Sin registrar". Dashboard, listado y reportes comparten la misma fuente.

| ID | Métrica | Cálculo |
|---|---|---|
| A1 | Total gastado del período | `df["monto"].sum()` |
| A2 | Variación vs. mes anterior | (total actual − total del mes anterior **a la misma fecha**) / total anterior × 100 (si el anterior es 0 → sin variación) |
| A3 | Distribución por categoría | `groupby("categoria").agg(cantidad, total)`; % = total / A1 × 100 |
| A4 | Distribución por método de pago | `groupby("metodo_pago")["monto"].sum()` con "Sin registrar" |
| A5 | Evolución diaria y acumulada | `resample("D").sum()` con relleno en cero y `cumsum()` |
| A6 | Evolución mensual (6 meses) | `resample("MS").sum()` de los últimos seis meses |
| A7 | Ejecución presupuestaria | ejecutado / planificado × 100 por categoría; estado según RN-05/RN-06 |
| A8 | Completitud | filas con los cinco campos / total × 100; campo con más omisiones |
| A9 | Presupuesto usado | Σ ejecutado / Σ planificado × 100 (solo categorías con presupuesto) |
| S1 | Gasto semanal apilado (nuevo, por el diseño) | gasto por día (lun–dom) y por categoría de la semana seleccionada + total por categoría y total general |

**P1 – Proyección al cierre (RF-17):**
```
ŷ(d) = b0 + b1·d,  d = 1..día actual (o último día con datos si el mes ya pasó), y = gasto acumulado al día d
b1, b0 = numpy.polyfit(d, y, 1)
P = b0 + b1·D,  D = días del mes
Solo si días con registros ≥ 7 y registros del mes ≥ 10 (RN-07); si no → "Datos insuficientes para proyectar".
```
Se presenta como "Estimación al ritmo actual", nunca como valor seguro.

**Reglas de recomendación (RF-18), prioridad ascendente, máximo 3 (RN-08):**
| ID | Condición | Mensaje | Prioridad | Acción (enlace) |
|---|---|---|---|---|
| R2 | Ejecutado > planificado en una categoría | "{categoría} superó su presupuesto en S/ {diferencia} ({%} %)." | 1 | Ver gastos de la categoría |
| R3 | Proyección suficiente > presupuesto total del mes | "Al ritmo actual cerrarías {mes} en S/ {proyección}, S/ {exceso} por encima de tu presupuesto." | 2 | Ver presupuesto |
| R1 | 80 % ≤ ejecutado/planificado ≤ 100 % | "Has usado el {%} % del presupuesto de {categoría}." | 3 | Ver presupuesto |
| R4 | Completitud del mes < 80 % | "{n} gastos están incompletos; el dato más omitido es {campo}." | 4 | Mis gastos filtrado por Incompleto |
| R5 | Categoría con aumento > 30 % vs. el mismo período del mes anterior y monto ≥ S/ 50 | "Tus gastos en {categoría} subieron {%} % respecto al mes pasado." | 5 | Ver gastos de la categoría |
| R7 | Categoría sin presupuesto con gasto > 20 % del total | "{categoría} no tiene presupuesto y representa el {%} % de tus gastos." | 5 | Definir presupuesto |
| R6 | Sin registros en los últimos 3 días del mes en curso | "No registras gastos desde el {fecha}. ¿Olvidaste anotar alguno?" | 6 | Registrar gasto |
Si ninguna se cumple: "Tus gastos están bajo control este mes". Los nombres de campo en mensajes van en lenguaje del usuario ("método de pago", no `metodo_pago`).

**Datos de verificación (deben convertirse en pruebas unitarias, son ficticios):**
- Doce gastos de octubre 2026 (fecha, monto, categoría, descripción, método):
  ```
  2026-10-01 190.00 Insumos y materia prima | Harina 2 sacos | Efectivo
  2026-10-01  24.00 Insumos y materia prima | (vacío)        | Efectivo
  2026-10-02  58.00 Servicios (luz, agua, gas) | Balón de gas 10 kg | (vacío)
  2026-10-03  15.00 Empaques y envases | Bolsas kraft x 100 | Yape
  2026-10-04 900.00 Alquiler | Alquiler del local | Transferencia bancaria
  2026-10-05  86.50 Insumos y materia prima | Mantequilla 5 kg | Yape
  2026-10-05   6.00 Transporte | Pasaje al mercado | Efectivo
  2026-10-06 212.30 Servicios (luz, agua, gas) | Recibo de luz | Transferencia bancaria
  2026-10-07  42.00 (vacío) | Azúcar 1 saco | Efectivo
  2026-10-08  18.00 Insumos y materia prima | Huevos 1 jaba | Plin
  2026-10-08  35.00 Empaques y envases | Cajas para tortas | Yape
  2026-10-09 280.00 Servicios (luz, agua, gas) | Recibo de agua y gas | (vacío)
  ```
  Presupuesto: Insumos 400.00 · Servicios 520.00 · Empaques 60.00 · Alquiler 900.00 · Transporte 50.00.
  Resultados esperados: completitud **66.7 %** (8/12), campo más omitido **método de pago** (2); Servicios 550.30 > 520.00 → **Excedida**; Empaques 50.00/60.00 = 83.3 % → **En alerta**; 4 de 5 categorías controladas; total del reporte **1,866.80**.
- Acumulado diario de 25 días (mes de 31 días):
  `[219.64, 329.47, 480.47, 604.02, 741.3, 1070.76, 1166.86, 1304.13, 1427.68, 1592.42, 1702.24, 1853.24, 1949.34, 2306.26, 2429.81, 2567.08, 2676.91, 2827.91, 2951.46, 3088.74, 3390.75, 3500.57, 3637.85, 3761.4, 3912.4]`
  Esperado: b1 = **156.2955**, b0 = **27.8672**, proyección = **S/ 4,873.03**; con presupuesto total 4,800.00 se activa **R3** (S/ 73.03 de exceso).
- Límites de estado: 79.9 % → Controlada; 80 % → En alerta; 100 % → En alerta (sigue controlada); 100.1 % → Excedida.
- Proyección con 6 días con registros o 9 registros → insuficiente.

Diseña los servicios de analítica como **funciones puras sobre DataFrames** (fáciles de probar sin base de datos) más una función que construye el DataFrame desde la BD.
