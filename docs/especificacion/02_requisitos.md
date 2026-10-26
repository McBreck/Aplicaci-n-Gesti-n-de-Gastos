# 02 — Requisitos funcionales y no funcionales

> Fuente: prompt maestro de implementación, secciones 7 y 8 (EDT 1.3).

## 7. Requisitos funcionales (EDT 1.3) con criterio de aceptación

| ID | Requisito | Criterio de aceptación |
|---|---|---|
| RF-01 | Iniciar sesión con correo y contraseña | Válidas → dashboard (o panel de usuarios si es admin); inválidas → "Correo o contraseña incorrectos" (mensaje genérico). |
| RF-02 | Cerrar sesión manual y automática tras 30 min de inactividad | Tras cerrar, ninguna página interna es accesible sin autenticarse. |
| RF-03 | Cambiar contraseña (vigente + nueva dos veces) | Política: mínimo 8 caracteres con letras y números; la anterior deja de funcionar. |
| RF-04 | Admin crea, edita, activa/desactiva y restablece contraseña de cuentas | Cuenta desactivada no ingresa ("Tu cuenta está desactivada. Comunícate con el administrador."); cuenta nueva ingresa con la contraseña temporal; correo duplicado → conflicto. |
| RF-05 | Registrar gasto: fecha (hoy por defecto), monto (obligatorio), categoría, descripción, método de pago | Se guarda con solo fecha y monto; monto vacío, 0 o negativo se rechaza con mensaje claro. |
| RF-06 | Señalar completitud al guardar/modificar | Estado "Completo" o "Incompleto" + lista de campos faltantes. |
| RF-07 | Modificar cualquier campo de un gasto propio | Al completar el faltante pasa de Incompleto a Completo. |
| RF-08 | Eliminar gasto propio con confirmación (lógico) | Desaparece de listados, reportes y gráficos; queda en auditoría. |
| RF-09 | Listar y filtrar por fechas, categoría, método, estado; buscar por descripción | Cada filtro reduce el listado y muestra el total del resultado. |
| RF-10 | % de completitud del período y campo más omitido | Coincide con RC / TR × 100. |
| RF-11 | Categorías: copia de predeterminadas por cuenta; crear y renombrar propias; desactivar cualquiera | Desactivada no aparece al registrar, se conserva en el historial. |
| RF-12 | Presupuesto mensual por categoría; copiar del mes anterior | Uno por categoría/mes/año; la copia replica los montos. |
| RF-13 | Comparar ejecutado vs. planificado y clasificar Controlada / Excedida | Coincide con la Ficha de registro N.° 1. |
| RF-14 | Alertas visuales al 80 % y al superar | Aparecen en dashboard y en presupuesto al cruzar cada umbral. |
| RF-15 | Dashboard: total del mes, % presupuesto usado, proyección, % completitud y gráficos | Valores iguales a los del reporte del mismo período. |
| RF-16 | Análisis descriptivo: por categoría, por método, evolución diaria y mensual, variación vs. mes anterior | La suma por categoría = total del período. |
| RF-17 | Proyección al cierre por regresión lineal sobre el acumulado diario | Con datos insuficientes: "Datos insuficientes para proyectar". |
| RF-18 | Hasta tres recomendaciones por reglas | Cada una corresponde a una regla cuya condición se cumple. |
| RF-19 | Reporte en pantalla: diario, semanal, mensual o personalizado; agrupado por categoría, método o fecha; totales y subtotales | Total = suma de los gastos del período. |
| RF-20 | Exportar el reporte a PDF con negocio, período, totales y fecha de emisión | El PDF contiene los mismos datos que la pantalla. |

Casos de uso: CU-01 Iniciar sesión · CU-02 Cerrar sesión · CU-03 Cambiar contraseña · CU-04 Gestionar usuarios · CU-05 Registrar gasto (incluye CU-15) · CU-06 Modificar gasto (incluye CU-15) · CU-07 Eliminar gasto · CU-08 Consultar gastos · CU-09 Gestionar categorías · CU-10 Definir presupuesto · CU-11 Visualizar dashboard · CU-12 Proyección y recomendaciones (extiende CU-11) · CU-13 Generar reporte · CU-14 Exportar PDF (extiende CU-13) · CU-15 Verificar completitud (incluido).

Flujos alternos que DEBES implementar: 4b bloqueo tras 5 intentos (CU-01); 4c cuenta desactivada (CU-01); 7a "Completar ahora" tras registro incompleto (CU-05); 4a "No hay gastos con estos filtros" + limpiar filtros (CU-08); 3a copiar mes anterior (CU-10); 2a panel vacío con invitación (CU-11); 1a y 3a de CU-12; 4a período sin gastos (CU-13); 2a error al generar PDF (CU-14).

## 8. Requisitos no funcionales que afectan el código (ISO/IEC 25010:2023)

| ID | Exigencia |
|---|---|
| RNF-01 | Reporte de un mes con hasta 500 registros mostrado en < 1 s (una consulta + Pandas, sin N+1). |
| RNF-02 | Páginas principales ≤ 3 s en 4G (assets locales, sin librerías innecesarias, Chart.js solo donde hay gráficos). |
| RNF-04 | Sin desplazamiento horizontal desde 360 px. |
| RNF-05 | Registrar un gasto en un solo formulario, a máximo 2 toques desde el dashboard. |
| RNF-06 | Mensajes en español claro, sin términos técnicos, indicando cómo corregir. |
| RNF-07 | Contraseñas solo como hash Argon2id. |
| RNF-08 | HTTPS en producción con redirección 301 desde HTTP. |
| RNF-09 | Cada usuario solo accede a sus datos (id ajeno → 404). |
| RNF-10 | CSRF en todos los formularios y POST; ORM con parámetros. |
| RNF-11 | Bloqueo de 15 min tras 5 intentos fallidos consecutivos. |
| RNF-12 | Auditoría de inicio de sesión, creación, modificación y eliminación (usuario, fecha y hora, IP). |
| RNF-13 | Disponibilidad ≥ 99 % (ruta `/salud`, servicio con reinicio automático). |
| RNF-14 | Respaldo diario con pg_dump, 7 copias (script en `deploy/`). |
| RNF-15 | MVC en tres capas, PEP 8, cobertura ≥ 70 % en `app/services`. |
| RNF-16 | Últimas dos versiones de Chrome, Edge, Firefox y Chrome Android. |
| RNF-17 | Stack de la sección 3; SQLite excluido. |
| RNF-18 | VPS Hostinger con Ubuntu, Nginx y Gunicorn, con dominio propio. |
| RNF-19 | Español, montos `S/ 1,234.56`, fechas `dd/mm/aaaa`, zona America/Lima. |
