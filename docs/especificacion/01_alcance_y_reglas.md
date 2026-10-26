# 01 — Alcance y reglas de negocio

> Fuente: prompt maestro de implementación, secciones 1, 2 y 6 (aprobadas en las fases 1.0 Análisis de requisitos y 2.0 Diseño de la EDT).

## 1. Contexto de la tesis

- Universidad Privada Antenor Orrego (UPAO), Trujillo, Perú. Ingeniería de Computación y Sistemas.
- Título: *"Aplicación web con técnicas de análisis de datos para mejorar la gestión de gastos en micro emprendedores de Trujillo 2026"*.
- Autores: Ponce Vásquez, McBreck; Rivera Chamorro, Kristel Catherine. Asesor: Dr. Cieza Mostacero, Segundo Edwin.
- Usuarios: microemprendedores de Trujillo (panaderías, bodegas, etc.), con poca familiaridad técnica y que usan principalmente el **celular**.
- Problemas que resuelve: registro diferido y de memoria, falta de trazabilidad, registros incompletos, consolidación manual lenta (más de 2 horas al mes), sin comparación con lo planificado, apuntes dispersos en fotos, excesos detectados tarde.
- Objetivos específicos e indicadores (medidos FUERA de la app):
  - OE1 – Eficacia en el control de gastos: `ECG = (NGCC / NTG) × 100` (una categoría está correctamente controlada si ejecutado ≤ planificado).
  - OE2 – Tiempo para generar un reporte de gastos: `TRG = Σ tᵢ / n` (meta: menos de 1 segundo).
  - OE3 – Completitud de los registros: `CRG = (RC / TR) × 100` (registro completo = fecha, monto, categoría, descripción y método de pago).
- La app debe **facilitar** estos resultados (presupuesto con estados, reportes rápidos, aviso de completitud), pero no los mide.
- Usabilidad: se aplicará el cuestionario SUS en papel/formulario externo (meta ≥ 68). No se implementa dentro de la app.

## 2. Alcance

**Dentro del alcance (solo gestión de gastos):** acceso y cuentas, registro de gastos con verificación de completitud, consulta y filtros, categorías, presupuesto mensual por categoría, comparación ejecutado vs. planificado, alertas, análisis descriptivo, proyección al cierre de mes, recomendaciones por reglas, dashboard, reportes en pantalla y en PDF, bitácora de auditoría.

**Fuera del alcance (no implementar nunca):** ventas e ingresos, cuentas por cobrar o por pagar, préstamos, inversiones, contabilidad, impuestos, facturación electrónica, inventario, nómina, captura de métricas de la investigación, registro público de usuarios (las cuentas las crea el administrador), recuperación de contraseña por correo.

## 6. Reglas de negocio

| ID | Regla |
|---|---|
| RN-01 | Un gasto está **completo** cuando tiene los cinco campos: fecha, monto, categoría, descripción y método de pago. |
| RN-02 | Solo fecha y monto son obligatorios para guardar; los demás pueden quedar vacíos y el registro se marca **Incompleto** con aviso de los campos faltantes. |
| RN-03 | Monto mayor que cero, máximo dos decimales (máximo 99 999 999.99). |
| RN-04 | La fecha no puede ser posterior a hoy en America/Lima. |
| RN-05 | Categoría **Controlada** en un mes si ejecutado ≤ planificado (mismo criterio de la Ficha de registro N.° 1). |
| RN-06 | **En alerta** cuando ejecutado ≥ 80 % de lo planificado (y ≤ 100 %); **Excedida** cuando lo supera. |
| RN-07 | La proyección solo se calcula con ≥ 7 días con registros y ≥ 10 registros en el mes consultado. |
| RN-08 | Máximo tres recomendaciones, ordenadas por prioridad. |
| RN-09 | Eliminación **lógica**: `eliminado = TRUE`, se excluye de listados, reportes y gráficos. |
| RN-10 | Un único presupuesto por usuario, categoría, mes y año. |
| RN-11 | Categorías predeterminadas: Insumos y materia prima, Mercadería, Servicios (luz, agua, gas), Alquiler, Transporte, Sueldos y pagos a terceros, Mantenimiento, Empaques y envases, Otros. Se copian a cada cuenta nueva con `predeterminada = TRUE`. |
| RN-12 | Métodos de pago: Efectivo, Yape, Plin, Transferencia bancaria, Tarjeta. |
| RN-13 | Cada usuario accede solo a sus datos; el administrador gestiona cuentas, **no ve gastos**. |
