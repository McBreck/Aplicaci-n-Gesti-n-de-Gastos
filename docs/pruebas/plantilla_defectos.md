# Registro de defectos (DEF-nn)

Un defecto es cualquier diferencia entre el resultado esperado de un caso de prueba (CP) y lo que hace la aplicación. Cada defecto recibe un código correlativo (DEF-01, DEF-02…) que no se reutiliza, aunque el defecto se rechace.

## Ciclo de un defecto

1. **Abierto:** se detecta y se registra con la ficha de abajo.
2. **En corrección:** se corrige en la rama `develop` con un commit `fix(4.x): descripción (DEF-nn)`, donde `4.x` es la EDT donde se detectó (por ejemplo, `fix(4.2): …`).
3. **Corregido:** el commit está subido y las pruebas automatizadas pasan.
4. **Verificado:** se repite el caso de prueba que falló y ahora pasa.
5. **Cerrado.** Si no era un defecto (por ejemplo, el resultado esperado estaba mal escrito), queda **Rechazado**; si repite otro, **Duplicado** (indica de cuál).

## Severidad

| Severidad | Cuándo |
|---|---|
| **Crítica** | Pérdida o exposición de datos, falla de seguridad o la aplicación no se puede usar. |
| **Alta** | Una función requerida (RF) no cumple su criterio de aceptación y no hay otra forma de lograrlo. |
| **Media** | La función se cumple con dificultad o con un resultado parcialmente incorrecto. |
| **Baja** | Problema visual, de texto o de comodidad que no impide usar la función. |

La **prioridad** (Alta, Media o Baja) indica el orden de corrección; normalmente sigue a la severidad.

## Ficha de defecto

Copia esta ficha por cada defecto.

| Campo | Valor |
|---|---|
| **Código** | DEF-__ |
| **Título** | (qué falla, en una línea) |
| **Fecha de detección** | dd/mm/aaaa |
| **Detectado por** | |
| **Caso de prueba** | CP-__ |
| **Requisito afectado** | RF-__ / RNF-__ / RN-__ |
| **Pantalla o ruta** | (por ejemplo, P-04 Mis gastos, `/gastos`) |
| **Entorno** | Local o producción · navegador y versión · dispositivo y ancho de pantalla |
| **Datos usados** | (cuenta PRUEBA, montos, fechas) |
| **Pasos para reproducirlo** | 1. … 2. … 3. … |
| **Resultado esperado** | (tal como figura en la lista del caso) |
| **Resultado obtenido** | |
| **Evidencia** | (captura o archivo, por ejemplo `DEF-03_captura.png`) |
| **Severidad / Prioridad** | |
| **Estado** | Abierto |
| **Corrección (commit)** | `fix(4.x): … (DEF-__)` — fecha |
| **Verificación** | Fecha y responsable de la nueva ejecución del caso |
| **Fecha de cierre** | |

## Resumen de defectos

| Código | Título | CP | Severidad | Estado | Commit de corrección | Fecha de cierre |
|---|---|---|---|---|---|---|
| DEF-01 | | | | | | |
| DEF-02 | | | | | | |
| DEF-03 | | | | | | |
