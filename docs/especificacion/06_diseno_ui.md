# 06 — Diseño de interfaz

> Fuente: prompt maestro de implementación, sección 11 (EDT 2.5 y 2.6, con el cambio CR-01).

## 11. Diseño de interfaz (OBLIGATORIO) — adaptación del sistema "Time Tracking Dashboard" a ControlGastos

Tomo como referencia visual un dashboard de seguimiento de tiempo con estilo **limpio, moderno y minimalista**. No copies su contenido: **adapta su lenguaje visual** a la gestión de gastos según esta tabla de equivalencias.

| Elemento de la referencia | Adaptación en ControlGastos |
|---|---|
| Logo círculo negro con "R" | Círculo negro con "C" blanca + texto "ControlGastos" |
| My Desk / Inbox (badge 3) / Everything / Track | Inicio (dashboard) · Mis gastos · Presupuesto (badge con nº de categorías En alerta o Excedidas) · Categorías · Reportes |
| Lista "Projects" con punto de color y horas | Lista "Categorías" con punto de color y **monto del mes** (S/) a la derecha |
| Widget "Free plan" con barra roja y botón "Upgrade" | Widget "Presupuesto de {mes}": "Has usado el {A9} %", barra de progreso con color de estado y botón píldora "Ver presupuesto" (sin presupuesto: "Aún no defines tu presupuesto" + "Definir presupuesto") |
| Título "Track" + avatar + menú "All" | Título de la página + selector de mes ("Octubre 2026") + avatar con iniciales y menú (Mi cuenta, Cerrar sesión) |
| Temporizador con botón Play, "00:00:00", "Select Project", "What are you working on?" | **Registro rápido**: botón circular negro "+" (guardar), monto grande "S/ 0.00", selector "Categoría", campo "¿En qué gastaste?", selector "Método de pago" y fecha (hoy por defecto) |
| 3 tarjetas de proyecto con +2m/+5m/+10m | 3 tarjetas de las **categorías más usadas** (últimos 30 días; si no hay datos, las 3 primeras activas) con su color, botón circular "+" y botones **"+S/ 5", "+S/ 10", "+S/ 20"** que SUMAN al monto del registro rápido y seleccionan esa categoría (no guardan solos) |
| Gráfico de barras apiladas por día y proyecto, con flechas de semana y leyenda con totales | **"Gastos de la semana"**: barras apiladas por día (lun–dom) y categoría (S1), flechas ‹ › para cambiar de semana, filtro "Todas las categorías", leyenda a la derecha con punto, categoría, total y fila "Total" |
| Registro de actividad agrupado por fecha con píldoras y duración | **"Actividad reciente"**: agrupado por "Hoy", "Ayer", "mié, 22 oct" con total del día a la derecha; filas con píldora de categoría, descripción (o "Sin descripción" en gris), etiqueta "Incompleto" si aplica y monto a la derecha; varios gastos de la misma categoría el mismo día se agrupan en "3 registros" con "+" para expandir |
| FAB negro de chat | **FAB negro "+"** fijo abajo a la derecha que abre "Registrar gasto" (cumple RNF-05: ≤ 2 toques) |

### 11.1 Tokens (en `app/static/css/app.css` como variables CSS que sobrescriben Bootstrap)
```
--cg-fondo: #F9FAFB;         /* fondo del área principal */
--cg-superficie: #FFFFFF;    /* tarjetas y barra lateral */
--cg-texto: #111827;         /* texto principal y cifras */
--cg-texto-2: #6B7280;       /* texto secundario, fechas, contadores */
--cg-borde: #E5E7EB;         /* bordes y divisores */
--cg-campo: #F3F4F6;         /* fondo de selectores y campos "sin borde" */
--cg-accion: #000000;        /* botón principal, botón "+", FAB */
--cg-peligro: #EF4444;       /* Excedida, eliminar, alertas */
--cg-radio-tarjeta: 12px;  --cg-radio-pildora: 20px;  --cg-radio-campo: 10px;
--cg-sombra: 0 1px 2px rgba(17,24,39,.04), 0 1px 3px rgba(17,24,39,.06);
```
Estados (siempre **color + ícono + palabra**, nunca solo color):
- Controlada / Completo: texto `#166534` sobre `#DCFCE7`, ícono `bi-check-circle`.
- En alerta / Incompleto: texto `#92400E` sobre `#FEF3C7`, ícono `bi-exclamation-triangle`.
- Excedida: texto `#991B1B` sobre `#FEE2E2`, ícono `bi-x-circle`.

Paleta de categorías (claras, como la referencia): `#8B7BFF #FFD166 #7EF0C0 #93C5FD #F9A8D4 #FDBA74 #BEF264 #67E8F9 #CBD5E1 #C4B5FD`. **Accesibilidad:** sobre estos fondos claros el texto va en `#111827` (no blanco como en la referencia, para cumplir contraste WCAG AA). Crea un filtro/función `color_texto(hex)` que devuelva `#111827` o `#FFFFFF` según la luminancia, por si el usuario elige colores oscuros.

### 11.2 Tipografía
Inter (woff2 local) con respaldo `system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`. Pesos 400, 500, 600. Tamaños: cifra grande del registro rápido y KPI 32 px con `font-variant-numeric: tabular-nums`; títulos de sección 16–18 px SemiBold; texto general 14 px; secundario, fechas y contadores 12–13 px. Todos los montos con números tabulares.

### 11.3 Layout general (`base.html`)
- **Escritorio (≥ 992 px):** dos columnas. Barra lateral fija de 260 px, fondo blanco, borde derecho `--cg-borde`: logo arriba; navegación con íconos outline (Bootstrap Icons) a la izquierda del texto; ítem activo con fondo blanco, borde gris suave, sombra sutil y texto SemiBold; sección "Categorías" (título pequeño gris) con punto de color, nombre y monto del mes; widget de presupuesto abajo. Área principal fluida con fondo `--cg-fondo`, cabecera superior (título a la izquierda; selector de mes y avatar a la derecha) y contenido con padding generoso (24–32 px).
- **Tableta (576–991 px):** barra lateral colapsada a solo íconos (72 px) con tooltips; tarjetas rápidas en 2 columnas.
- **Celular (< 576 px):** barra lateral oculta → botón hamburguesa que abre un *offcanvas* de Bootstrap con el mismo contenido; tarjetas rápidas en 1 columna; KPI en 2×2; los contenedores de gráficos con `overflow-x: auto` y ancho mínimo de 560 px (el desplazamiento horizontal ocurre SOLO dentro del gráfico, nunca en la página: RNF-04); FAB "+" siempre visible.
- Administrador: misma plantilla, navegación solo con "Usuarios" y "Mi cuenta"; sin categorías ni widget de presupuesto.
- Mensajes flash como *toasts* arriba a la derecha (abajo en celular), con ícono de estado; el toast de gasto incompleto incluye el botón "Completar ahora".
- Áreas táctiles ≥ 44 px, foco visible, `label` en todos los campos (pueden ser visualmente ocultos donde el diseño usa placeholder), `aria-label` en botones de solo ícono, `lang="es"`.

### 11.4 Componentes reutilizables (en `templates/componentes/` como macros Jinja2)
`tarjeta`, `kpi`, `chip_estado`, `pildora_categoria`, `barra_presupuesto` (barra con marca vertical en 100 %, escala hasta 125 %, relleno con color del estado), `registro_rapido`, `tarjeta_categoria_rapida`, `actividad` (lista agrupada por fecha), `estado_vacio` (ícono + texto + botón), `modal_confirmacion` (Bootstrap modal, nunca `confirm()` del navegador), `paginacion`, `filtros_gastos`.
Botones: principal = píldora negra con texto blanco; secundario = píldora blanca con borde `--cg-borde`; peligro = píldora roja `--cg-peligro`. Campos "suaves": fondo `--cg-campo`, sin borde, radio 10 px, borde de 2 px negro al enfocar.

### 11.5 Pantallas (EDT 2.6, ahora con este diseño)
- **P-01 Inicio de sesión:** fondo `--cg-fondo`, tarjeta blanca centrada (máx. 400 px) con logo, "Ingresa a ControlGastos", correo, contraseña con botón mostrar/ocultar, botón negro "Ingresar". Errores: genérico; bloqueo: "Por seguridad, tu cuenta está bloqueada. Inténtalo de nuevo en {n} minutos."; desactivada: mensaje del RF-04. Mensaje "Sesión cerrada" tras cerrar.
- **P-02 Dashboard (Inicio):** orden de arriba hacia abajo:
  1. Registro rápido (ancho completo).
  2. Tres tarjetas de categorías rápidas.
  3. Cuatro KPI: "Gastado en {mes}" (A1 + texto de A2: "12.4 % más que a la misma fecha de {mes anterior}"); "Presupuesto usado" (A9 + barra); "Proyección al cierre" (P1 + "estimación al ritmo actual" o "Datos insuficientes para proyectar"); "Registros completos" (A8 + "dato más omitido: {campo}").
  4. Fila 2/3 + 1/3: "Gastos de la semana" (S1, barras apiladas) | "Recomendaciones" (hasta 3, ícono con fondo del color de estado, texto y enlace de acción).
  5. Fila 2/3 + 1/3: "Gasto acumulado del mes" (línea real `#111827` 2 px, proyección punteada `#8B7BFF` [6,5] hasta fin de mes, presupuesto total como línea gris `#9CA3AF` [2,3]; eje Y desde 0 en S/; tooltip por día) | "Presupuesto por categoría" (las 5 con mayor % con `barra_presupuesto` y chip de estado; enlace "Ver todo").
  6. Fila 2/3 + 1/3: "Actividad reciente" (últimos 7 días) | "Método de pago" (barras horizontales de una sola serie `#111827`, "Sin registrar" en `#D1D5DB`, sin leyenda).
  Estados especiales: mes sin gastos → tarjetas en S/ 0.00 y "Aún no registras gastos este mes" + botón; sin presupuesto → "Define tu presupuesto para ver si te mantienes dentro de lo planificado"; error al cargar gráficos → "No se pudieron cargar los gráficos. Vuelve a intentarlo" + botón reintentar (las cifras del servidor se conservan). Las cifras de KPI se renderizan en el servidor; los gráficos se cargan por `fetch` a `/api/dashboard`.
- **P-03 Registrar / editar gasto:** página de un solo formulario: monto grande con `inputmode="decimal"` (acepta coma o punto), fecha (hoy), **categorías como botones grandes** con su color (no lista desplegable), **métodos de pago como botones** (Efectivo, Yape, Plin, Transferencia, Tarjeta), descripción con contador de caracteres, texto de ayuda bajo cada campo, botón negro "Guardar". En edición, los campos vacíos se resaltan en ámbar con "Falta completar". Tras guardar: toast "Gasto guardado · Completo" o "Gasto guardado · Incompleto: falta {campos}" con "Completar ahora". La categoría desactivada no aparece al registrar, pero si el gasto ya la tiene se muestra en edición.
- **P-04 Mis gastos:** cabecera con total del resultado, % de completitud (A8 del filtro) y campo más omitido; barra de filtros (desde, hasta, categoría, método, estado Completo/Incompleto, búsqueda por descripción) que en celular se pliega en "Filtros"; listado con el componente `actividad` agrupado por fecha (50 por página), cada fila abre la edición; acciones Editar / Eliminar (modal con fecha, monto y descripción). Sin resultados: "No hay gastos con estos filtros" + "Limpiar filtros". Por defecto: mes actual, del más reciente al más antiguo.
- **P-05 Presupuesto del mes:** selector de mes; resumen (total planificado, total ejecutado, A9); tabla/lista por categoría activa: punto de color, nombre, campo de monto planificado, ejecutado, `barra_presupuesto`, % y chip de estado; botones "Copiar del mes anterior" (secundario) y "Guardar" (negro). Montos ≥ 0; vacío = sin presupuesto.
- **P-06 Categorías:** lista con punto de color, nombre, etiqueta "Predeterminada" si aplica, interruptor Activa/Inactiva, "Renombrar" solo en las propias; formulario "Nueva categoría" con nombre y selector de color por muestras de la paleta. Nombre repetido (sin distinguir mayúsculas): "Ya tienes una categoría con ese nombre".
- **P-07 Reportes:** selector de período en píldoras segmentadas (Diario, Semanal, Mensual, Personalizado con fechas), agrupación (Categoría, Método de pago, Fecha) y botón negro "Generar reporte"; resultado en tarjeta con encabezado (negocio, período, fecha de emisión), tabla (grupo con punto de color si es categoría, cantidad, total, %), fila Total destacada y botón "Descargar PDF". Período sin gastos: "No hay gastos registrados en este período".
- **P-08 Administración de usuarios:** tabla (nombre, negocio, rubro, correo, chip Activa/Inactiva, último acceso dd/mm/aaaa HH:MM), botones Editar, Activar/Desactivar, Restablecer contraseña (muestra la contraseña temporal UNA vez); "Nuevo usuario" con nombre, correo, negocio, rubro, contraseña temporal.
- **P-09 Mi cuenta:** datos del usuario (solo lectura) y formulario de cambio de contraseña con la política visible.

### 11.6 Gráficos (Chart.js 4, archivo `static/js/dashboard.js`)
- Configuración común: fuente Inter 12 px, color `#6B7280`, cuadrícula horizontal `#E5E7EB`, sin cuadrícula vertical, `maintainAspectRatio: false`, tooltips con montos `S/ 1,234.56`.
- Apilado semanal: `type: 'bar'`, `stacked: true` en x e y, un dataset por categoría con su color, `borderRadius: 6`, `maxBarThickness: 28`, leyenda nativa oculta (se dibuja la leyenda HTML con totales).
- Respeta `prefers-reduced-motion` (sin animación).

### 11.7 Formatos y textos
Filtros Jinja2: `soles` → `S/ 1,234.56`; `fecha` → `26/10/2026`; `fecha_corta` → `lun, 26 oct`; `mes_anio` → `Octubre 2026`. Nombres de días y meses en español con tablas propias (no dependas del *locale* del sistema operativo). Textos siempre en segunda persona y lenguaje sencillo ("Registrar gasto", "Mis gastos", "¿En qué gastaste?").

### 11.8 Lo que NO cambia del diseño aprobado
Las pantallas P-01 a P-09, los contenidos del dashboard de EDT 2.5 (4 KPI, presupuesto por categoría con marca de lo planificado, recomendaciones con acción, acumulado con proyección punteada, método de pago), los estados especiales y la regla "el estado nunca depende solo del color".

### 11.9 Registro del cambio (evidencia de retroalimentación en cascada)
En la Etapa 3.2 crea `docs/cambios/CR-01_diseno_interfaz.md` con: código CR-01, fecha, fase que origina (3.0 Implementación) y fase afectada (2.0 Diseño: EDT 2.2, 2.5 y 2.6), descripción (adopción del estilo minimalista de referencia, colores por categoría, registro rápido, tarjetas rápidas, gráfico semanal apilado, actividad agrupada y FAB), justificación (registro más rápido en celular para RNF-05, identificación visual de categorías, mejor lectura de la actividad diaria), impacto (sin cambios en RF, CU ni reglas; se agrega la métrica S1 de visualización; el color por defecto de categoría pasa de `#2A78D6` a la paleta nueva) y estado "Aprobado por los investigadores".
