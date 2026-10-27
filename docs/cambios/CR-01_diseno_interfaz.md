# CR-01 — Adopción del diseño de interfaz minimalista

| Campo | Valor |
|---|---|
| Código | CR-01 |
| Fecha | 26/10/2026 |
| Fase que origina | 3.0 Implementación (EDT 3.2 Acceso, administración e interfaz base) |
| Fase afectada | 2.0 Diseño: EDT 2.2 (Modelo de datos), EDT 2.5 (Diseño del dashboard) y EDT 2.6 (Diseño de pantallas) |
| Tipo | Retroalimentación de cascada (de una fase posterior hacia una anterior) |
| Estado | Aprobado por los investigadores |

## Descripción

Se adapta a ControlGastos el lenguaje visual de un dashboard de referencia de estilo limpio, moderno y minimalista. Solo se toma el estilo, no el contenido. Incluye:

- **Estilo general:** barra lateral blanca con navegación por íconos, tarjetas blancas con bordes suaves sobre fondo gris claro, botones en forma de píldora negra y tipografía Inter con números tabulares.
- **Colores por categoría:** cada categoría tiene un color propio de una paleta clara (`#8B7BFF`, `#FFD166`, `#7EF0C0`, `#93C5FD`, `#F9A8D4`, `#FDBA74`, `#BEF264`, `#67E8F9`, `#CBD5E1`, `#C4B5FD`). Se usa en píldoras, puntos de color y gráficos.
- **Registro rápido** en el dashboard: monto grande, categoría, descripción, método de pago y fecha, con botón circular "+".
- **Tarjetas rápidas** de las tres categorías más usadas, con botones "+S/ 5", "+S/ 10" y "+S/ 20" que suman al monto del registro rápido.
- **Gráfico semanal apilado** "Gastos de la semana": barras por día (lunes a domingo) y categoría, con leyenda de totales.
- **Actividad agrupada** por fecha ("Hoy", "Ayer", "mié, 21 oct") con total del día y píldoras de categoría.
- **Botón flotante (FAB) "+"** fijo abajo a la derecha que abre "Registrar gasto".

## Justificación

1. **Registro más rápido en el celular (RNF-05).** El FAB y el registro rápido dejan el formulario de gasto a uno o dos toques desde cualquier pantalla. Esto favorece el registro oportuno y completo de los gastos (OE3).
2. **Identificación visual de categorías.** El color propio de cada categoría permite reconocerla en listados, gráficos y reportes sin leer el nombre.
3. **Mejor lectura de la actividad diaria.** Agrupar por fecha con totales y ver la semana apilada facilita detectar a tiempo días o categorías con gasto inusual.
4. **Accesibilidad.** Sobre los fondos claros de la paleta el texto se muestra en `#111827` para cumplir el contraste WCAG AA. Los estados se comunican siempre con color, ícono y palabra.

## Impacto

| Elemento | Impacto |
|---|---|
| Requisitos funcionales (RF-01 a RF-20) | Sin cambios |
| Casos de uso (CU-01 a CU-15) | Sin cambios |
| Reglas de negocio (RN-01 a RN-13) | Sin cambios |
| Requisitos no funcionales | Sin cambios; se refuerza el cumplimiento de RNF-04, RNF-05 y RNF-06 |
| EDT 2.2 Modelo de datos | El color por defecto de la columna `categoria.color` pasa de `#2A78D6` (igual para todas) a `#8B7BFF`. Cada categoría de la plantilla recibe su propio color de la paleta nueva. No cambia la estructura de las tablas. |
| EDT 2.4 Analítica | Se agrega la métrica de visualización **S1 – Gasto semanal apilado** (gasto por día y categoría de la semana seleccionada, con totales). No altera A1–A9, P1 ni R1–R7. |
| EDT 2.5 Dashboard | Se agregan el registro rápido, las tarjetas rápidas, el gráfico semanal y la actividad reciente. Se conservan los 4 KPI, el presupuesto por categoría con marca de lo planificado, las recomendaciones con acción, el acumulado con proyección punteada y el gráfico por método de pago. |
| EDT 2.6 Pantallas | P-01 a P-09 se mantienen con el nuevo estilo. Las categorías y los métodos de pago se eligen con botones grandes en P-03. |

## Trazabilidad en el código

- Tokens de diseño y componentes: `app/static/css/app.css`, `app/templates/componentes/`.
- Layout (barra lateral, offcanvas, cabecera, toasts, FAB): `app/templates/base.html`.
- Colores de la plantilla de categorías: `migrations/versions/0001_esquema_inicial.py`.
- Contraste de texto sobre el color de la categoría: filtro `color_texto` en `app/services/formato.py`.
