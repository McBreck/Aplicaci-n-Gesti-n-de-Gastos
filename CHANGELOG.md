# Historial de cambios

Todos los cambios relevantes de ControlGastos se registran en este archivo, agrupados por etapa de la EDT (fase 3.0 Implementación en adelante).

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Secciones por entrada: **Agregado**, **Cambiado**, **Corregido**, **Eliminado**, **Seguridad**.

## [EDT 5.1–5.3] Preparación del despliegue en Hostinger — 26/10/2026

### Agregado
- `deploy/`, todo listo para el VPS, sin ejecutar nada en ningún servidor:
  - `scripts/instalar_servidor.sh` (idempotente) instala y configura:
    - actualizaciones y zona horaria de Lima;
    - el usuario `controlgastos`, sin acceso por SSH;
    - UFW con 22, 80 y 443, y SSH solo con llave;
    - PostgreSQL 16, Python 3.11 (deadsnakes o uv), Nginx y Certbot;
  - `scripts/desplegar.sh`: código de `main`, dependencias, respaldo previo, migraciones, reinicio y comprobación de `/salud`;
  - `scripts/respaldo_bd.sh`: `pg_dump -Fc` que conserva los 7 más recientes, con su línea de cron a las 02:30;
  - `scripts/restaurar_bd.sh`: prueba en una base aparte, o restauración real con confirmación;
  - `systemd/controlgastos.service`: Gunicorn con 3 workers, reinicio automático y endurecimiento básico;
  - `nginx/controlgastos.conf`: plantilla con `DOMINIO`, socket Unix, estáticos con caché de 7 días, gzip y cabeceras de seguridad; Certbot agrega el HTTPS;
  - `.env.example` de producción.
- `.github/workflows/deploy.yml`: despliegue manual por SSH (`workflow_dispatch`). Está desactivado hasta que se defina la variable `DESPLIEGUE_HABILITADO`.
- `docs/DESPLIEGUE_HOSTINGER.md`: guía para principiantes (5.1, 5.2 y 5.3) con:
  - las evidencias de cada paso;
  - los despliegues siguientes;
  - el mantenimiento y la solución de problemas frecuentes.
- Integración continua: shellcheck de los scripts y arranque en modo producción con Gunicorn. Se comprueba `/salud`, la redirección 301 y que no arranca sin `SECRET_KEY`.

### Cambiado
- `gunicorn.conf.py` crea el socket con `umask` 007: solo el grupo de Nginx (www-data) puede usarlo.

## [EDT 4.1–4.7] Soporte a la fase de pruebas — 26/10/2026

### Agregado
- `docs/pruebas/` para la fase 4.0:
  - índice con el catálogo CP-01 a CP-34 (requisitos, tipo de prueba y documento);
  - 4.2 pruebas funcionales: CP-01 a CP-27 con pasos, resultado esperado y el comando de sus pruebas automatizadas;
  - 4.4 rendimiento: cronometraje manual de CP-28, con 10 repeticiones y el promedio menor que 1 s como criterio;
  - 4.5 seguridad: CP-29 a CP-32 y revisión OWASP Top 10 2021;
  - 4.6 responsivo y SUS: matriz de pantallas por ancho y navegador (CP-33) y cuestionario SUS con su cálculo (CP-34, fuera de la app);
  - plantilla de defectos DEF-nn con severidad, estados y el commit de corrección.
- `flask demo rendimiento`: cuenta "PRUEBA Rendimiento" con 500 gastos en un mes (el anterior, o el de `--mes AAAA-MM`) para CP-28. Valida el mes antes de pedir la contraseña.
- Pruebas automatizadas:
  - CP-30 revisa todas las rutas POST de la aplicación, también las que se agreguen después;
  - CP-32 comprueba en modo producción la redirección a HTTPS con 301, HSTS y la cookie segura;
  - la prueba orientativa de rendimiento y la de acceso a reportes llevan su código (CP-28 y CP-29);
  - `tests/test_trazabilidad.py` falla si un caso entre CP-01 y CP-32 queda sin prueba.
- flake8 7.4.1 en `requirements-dev.txt` y un paso de estilo PEP 8 en la integración continua.

### Cambiado
- En producción, la aplicación redirige de HTTP a HTTPS con 301 (antes 302), como pide RNF-08.

## [EDT 3.8] Pruebas unitarias y cierre de la fase 3.0 — 26/10/2026

### Agregado
- `flask demo crear`: cuenta "PRUEBA Panadería" (`prueba.panaderia@controlgastos.test`), con una contraseña que se elige al crearla, que incluye:
  - unos 120 gastos de panadería en los 60 días hasta hoy;
  - cerca del 20 % incompletos, con el método de pago como dato más omitido;
  - el presupuesto de cada mes del período, con montos justos para que se vean las alertas, la proyección y las recomendaciones.

  Los datos salen de una semilla fija y se guardan en una sola transacción; si la cuenta ya existe, no se crea de nuevo.
- `flask demo borrar`: muestra las cuentas cuyo nombre empieza con "PRUEBA" y, al confirmar, las borra por completo con sus gastos, presupuestos, categorías y eventos de la bitácora (`--si` para no preguntar). Las demás cuentas y la plantilla de categorías no se tocan.
- Pruebas unitarias de AuthService, AuditoriaService, `periodo`, `validacion` y de los datos de demostración, más los casos que faltaban en analítica, categorías, formato y usuarios. Cada servicio tiene su archivo en `tests/unit/`.
- `setup.cfg` con la configuración de flake8 y pycodestyle: PEP 8 con líneas de hasta 120 caracteres (RNF-15).
- README con variables de entorno, pantallas, datos de demostración, pruebas y calidad, y estructura del proyecto.

### Cambiado
- Se partieron las líneas de más de 120 caracteres en servicios, rutas y pruebas, sin cambios de comportamiento.

## [EDT 3.7] Reportes y PDF — 26/10/2026

### Agregado
- P-07 Reportes (RF-19, RF-20; CU-13, CU-14):
  - período en píldoras: Diario y Semanal con una fecha (la semana va de lunes a domingo), Mensual con los últimos 24 meses y Personalizado con "Desde" y "Hasta";
  - agrupación por categoría (con punto de color), método de pago o fecha (solo los días con gastos);
  - resultado en una tarjeta con negocio, período, fecha de emisión, tabla con cantidad, total y %, fila Total destacada (= suma de los gastos del período) y botón "Descargar PDF";
  - período sin gastos: "No hay gastos registrados en este período", sin botón de PDF (flujo alterno 4a de CU-13);
  - Personalizado sin las dos fechas pide elegirlas; si "Desde" es posterior a "Hasta", se intercambian con un aviso;
  - en el celular la cantidad se muestra bajo el nombre del grupo para que la tabla no desborde (RNF-04).
- `ReporteService` (`services/reporte.py`):
  - `interpretar_solicitud` convierte la URL en período y agrupación; la misma solicitud arma la pantalla y el PDF;
  - `generar` usa el DataFrame de la analítica, así el total coincide con el dashboard del mismo período;
  - `generar_pdf` arma un A4 con ReportLab: negocio (o el nombre del usuario si no tiene negocio), "Reporte de gastos", período, agrupación, fecha de emisión en America/Lima, tabla con el encabezado repetido en cada página, fila Total, "Total del período: S/ … (N gastos)" y pie "Generado por ControlGastos" con el número de página.
- `/reportes/pdf` descarga `reporte_gastos_AAAAMMDD_AAAAMMDD.pdf`, armado en memoria. Si falla, muestra "No se pudo generar el PDF. Vuelve a intentarlo." y vuelve al reporte (flujo alterno 2a de CU-14).
- `analitica.por_fecha`: cantidad, total y % por día con gastos.
- Pruebas CP-26 y CP-27, y prueba orientativa de RNF-01: el reporte de 500 gastos se genera en menos de 1 s con cada agrupación. `tests/utilidades_pdf.py` lee el texto de los PDF con la biblioteca estándar.

### Seguridad
- El reporte y el PDF solo leen los gastos del usuario autenticado; el administrador recibe 403.
- El texto del usuario (como el nombre del negocio) se escapa antes de pasarlo a ReportLab, y el PDF se descarga con `Cache-Control: no-store`.

## [EDT 3.6] Dashboard — 26/10/2026

### Agregado
- P-02 Dashboard completo (RF-13 a RF-18; CU-11, CU-12), en este orden:
  1. registro rápido;
  2. tres tarjetas de las categorías más usadas en los últimos 30 días, con "+S/ 5", "+S/ 10" y "+S/ 20" que suman al monto y eligen la categoría sin guardar (RNF-05);
  3. cuatro KPI dibujados en el servidor: gastado en el mes con su variación frente al mes anterior a la misma fecha (A1, A2), presupuesto usado con barra y estado (A9), proyección al cierre (P1) y registros completos con el dato más omitido (A8);
  4. "Gastos de la semana" en barras apiladas por día y categoría (S1), con flechas de semana, filtro por categoría y leyenda con totales; al lado, hasta tres recomendaciones con ícono del color de su estado y enlace de acción;
  5. "Gasto acumulado del mes" con la línea real, la proyección punteada y el presupuesto total; al lado, las cinco categorías con mayor ejecución;
  6. "Actividad reciente" de los últimos 7 días, agrupada por día y por categoría ("3 registros"); al lado, "Método de pago" en barras horizontales con "Sin registrar" en gris.
- Selector de mes en la cabecera; no permite meses futuros.
- `/api/dashboard?mes=AAAA-MM&semana=AAAA-MM-DD`: datos de los gráficos solo del usuario autenticado; errores en JSON (401 sin sesión, 403 para el administrador).
- `static/js/dashboard.js` con Chart.js 4.4.9:
  - fuente Inter, montos `S/ 1,234.56` en los tooltips;
  - sin animación si el usuario prefiere menos movimiento;
  - Chart.js se carga solo en el dashboard (RNF-02).
- Estados especiales:
  - mes sin gastos: "Aún no registras gastos este mes" con botón (flujo alterno 2a);
  - sin presupuesto: "Define tu presupuesto para ver si te mantienes dentro de lo planificado";
  - error al cargar los gráficos: "No se pudieron cargar los gráficos. Vuelve a intentarlo" con "Reintentar", sin perder las cifras.
- En el celular los KPI van en 2×2, las tarjetas en una columna y los gráficos se desplazan dentro de su contenedor (RNF-04).
- El formulario P-03 acepta `?categoria=` para llegar con la categoría marcada.

## [EDT 3.5] Analítica, proyección y recomendaciones — 26/10/2026

### Agregado
- `AnaliticaService` (RF-15, RF-16):
  - un DataFrame por consulta parametrizada: gastos vigentes del usuario unidos con categoría y método, con "Sin categoría" y "Sin registrar";
  - métricas como funciones puras: A1 total, A2 variación frente al mes anterior a la misma fecha, A3 por categoría (la suma da A1), A4 por método de pago, A5 evolución diaria y acumulada, A6 evolución de seis meses, A7 ejecución presupuestaria, A8 completitud, A9 presupuesto usado y S1 gasto semanal apilado.
- `ProyeccionService` (P1, RF-17, RN-07): regresión lineal del acumulado con `numpy.polyfit`, solo con al menos 7 días con registros y 10 registros; si no, "Datos insuficientes para proyectar".
- `RecomendacionService` (RF-18, RN-08):
  - reglas R1 a R7 con su prioridad, mensaje y enlace de acción;
  - como máximo tres;
  - lista vacía = "Tus gastos están bajo control este mes".
- `analizar_mes()`: todas las métricas, la proyección y las recomendaciones de un mes con dos consultas (seis meses de gastos y el presupuesto del mes), para el dashboard de la EDT 3.6.
- `calculo.py`: montos en soles y porcentajes con redondeo "mitad hacia arriba", compartidos por el listado, el presupuesto y la analítica.
- Pruebas con todos los valores de verificación de la sección 9, por ejemplo b1 = 156.2955, b0 = 27.8672 y P = S/ 4,873.03 con R3 por S/ 73.03.

### Cambiado
- Los porcentajes de completitud (A8) y de ejecución presupuestaria usan el redondeo compartido de `calculo.py`.

## [EDT 3.4] Categorías, presupuesto y alertas — 26/10/2026

### Agregado
- P-06 Categorías (RF-11, CU-09):
  - lista con punto de color, etiqueta "Predeterminada" e interruptor Activa/Inactiva;
  - "Renombrar" solo en las categorías propias;
  - "Nueva categoría" con nombre y muestras de la paleta;
  - un nombre repetido (sin distinguir mayúsculas) muestra "Ya tienes una categoría con ese nombre".
- P-05 Presupuesto del mes (RF-12 a RF-14, CU-10):
  - selector de mes ‹ Octubre 2026 ›;
  - resumen con lo planificado, lo ejecutado y el presupuesto usado (A9);
  - una fila por categoría con monto planificado editable, ejecutado, barra con marca en el 100 %, porcentaje y estado (Controlada, En alerta o Excedida, siempre con ícono y palabra);
  - "Copiar del mes anterior" con confirmación (flujo alterno 3a);
  - un campo vacío significa "sin presupuesto" y se acepta 0.
- Alertas visuales al llegar al 80 % y al superar lo planificado (RF-14): avisos en P-05, badge en "Presupuesto" con la cantidad de categorías en alerta o excedidas, y widget de la barra lateral.
- Barra lateral del microemprendedor: lista "Categorías" con el monto del mes (cada una abre sus gastos) y widget "Presupuesto de {mes}" ("Has usado el … %", o "Aún no defines tu presupuesto" con "Definir presupuesto").
- `PresupuestoService`:
  - comparación ejecutado vs. planificado en tres consultas;
  - estados según RN-05 y RN-06;
  - guardado con un solo presupuesto por categoría y mes (RN-10);
  - copia del mes anterior;
  - bitácora con los montos anteriores y nuevos.
- `CategoriaService`: crear, renombrar, activar y desactivar, con bitácora.
- Módulos compartidos `validacion.py` (montos y errores por campo) y `periodo.py` (meses), y el componente `selector_mes`.

### Cambiado
- `requirements.txt` fija las dependencias indirectas SQLAlchemy 2.1.6, alembic 1.20.1 y limits 5.8.0 (decisión de los investigadores).

## [EDT 3.3] Gastos y completitud — 26/10/2026

### Agregado
- P-03 Registrar y editar gasto (RF-05 a RF-07, CU-05, CU-06) en un solo formulario:
  - monto grande que acepta coma o punto;
  - fecha de hoy por defecto;
  - categorías y métodos de pago como botones grandes;
  - descripción con contador de caracteres y ayuda bajo cada campo.
- Edición de gastos: los campos vacíos se resaltan en ámbar con "Falta completar". Una categoría desactivada se muestra al editar, pero no al registrar.
- Aviso de completitud al guardar (RF-06, CU-15): "Gasto guardado · Completo" o "Gasto guardado · Incompleto: falta …", con el botón "Completar ahora" (flujo alterno 7a).
- Eliminación lógica con modal de confirmación (RF-08, CU-07, RN-09): el gasto desaparece de los listados y queda en la bitácora.
- P-04 Mis gastos (RF-09, RF-10, CU-08):
  - total del resultado, % de registros completos (A8) y dato más omitido;
  - filtros por fechas, categoría (incluida "Sin categoría"), método de pago (incluido "Sin registrar"), estado y búsqueda en la descripción, que no distingue tildes ni mayúsculas;
  - en el celular, los filtros se pliegan en "Filtros";
  - 50 gastos por página, del más reciente al más antiguo; por defecto se muestra el mes actual;
  - si no hay resultados: "No hay gastos con estos filtros" + "Limpiar filtros" (flujo alterno 4a).
- Componentes `actividad` (agrupación por "Hoy", "Ayer" o fecha, con total del día y agrupación opcional en "N registros" de una misma categoría), `registro_rapido` y `filtros_gastos`.
- El registro rápido aparece arriba del inicio (punto 1 de P-02).
- `GastoService`:
  - validación de RN-02 a RN-04 que devuelve todos los errores a la vez;
  - listado con tres consultas fijas por página (sin N+1);
  - completitud A8 con desempate en el orden de RN-01;
  - bitácora CREAR, MODIFICAR y ELIMINAR con los valores anteriores y nuevos.
- `CategoriaService` con las consultas que necesita el registro (la gestión completa llega en la EDT 3.4).
- Filtro `porcentaje` ("66.7 %").

### Seguridad
- Las rutas de gastos son solo para microemprendedores (el administrador recibe 403). Un gasto ajeno o eliminado responde 404 (RNF-09).
- Solo se aceptan categorías del propio usuario.

## [EDT 3.2] Acceso, administración e interfaz base — 26/10/2026

### Agregado
- Sistema de diseño de la sección 11 (cambio CR-01):
  - tokens CSS sobre Bootstrap e Inter local;
  - barra lateral de 260 px, compacta (72 px, con tooltips) en tableta y *offcanvas* en celular;
  - cabecera con avatar y menú de usuario, toasts con botón de acción opcional, FAB y modal de confirmación.
- Macros reutilizables: `tarjeta`, `kpi`, `chip_estado`, `punto_color`, `pildora_categoria`, `barra_presupuesto`, `estado_vacio`, `modal_confirmacion`, `paginacion`, más campos de formulario accesibles.
- P-01 Inicio de sesión (RF-01, CU-01) con mostrar/ocultar contraseña y los flujos alternos 4b (bloqueo) y 4c (cuenta desactivada).
- Cierre de sesión manual por POST y automático tras 30 minutos sin actividad (RF-02, CU-02).
- P-09 Mi cuenta y cambio de contraseña con la política visible (RF-03, CU-03).
- P-08 Administración de usuarios (RF-04, CU-04):
  - alta con contraseña temporal y copia de las 9 categorías predeterminadas (RN-11);
  - edición, activación y desactivación;
  - restablecimiento con contraseña temporal mostrada una sola vez;
  - correo duplicado → 409.
- `AuthService`, `UsuarioService` y `AuditoriaService`. Bitácora de INICIO_SESION, CIERRE_SESION, LOGIN_FALLIDO, CREAR, MODIFICAR, ACTIVAR, DESACTIVAR y RESTABLECER, con IP (RNF-12).
- Páginas de error 400, 403, 404, 405, 429 y 500 con el diseño de la app y sin trazas.
- Página de inicio provisional del microemprendedor (el dashboard completo llega en la EDT 3.6).
- Filtro `fecha_hora` (dd/mm/aaaa HH:MM en hora de Lima).
- Registro del cambio `docs/cambios/CR-01_diseno_interfaz.md`.

### Seguridad
- Sesión obligatoria en todas las rutas salvo `/login` y `/salud`, mediante un guardián global (A01).
- `rol_requerido`: un microemprendedor recibe 403 en las rutas de administración.
- `obtener_propio_o_404` para los datos de cada usuario (RNF-09).
- Bloqueo de 15 minutos tras 5 intentos fallidos (RNF-11) y límite de 10 intentos de inicio de sesión por minuto e IP (A04).
- Sesión regenerada al ingresar (evita la fijación de sesión); una cuenta desactivada pierde la sesión abierta.
- `?next=` solo admite rutas internas.
- Rehash Argon2id si cambian los parámetros. Un correo inexistente tarda lo mismo que uno real.
- CSRF en todos los formularios y acciones POST (RNF-10). Las contraseñas nunca se registran en la bitácora.

## [EDT 3.1] Entorno, estructura y base de datos — 26/10/2026

### Agregado
- Fábrica `create_app()` con configuración por entorno (`APP_ENV`: desarrollo, pruebas, produccion) leída desde `.env`; se niega a arrancar si la URL de la base no es PostgreSQL (RNF-17) o si falta `SECRET_KEY`.
- Extensiones: SQLAlchemy 2, Flask-Migrate, Flask-Login, CSRFProtect, Flask-Limiter y Flask-Talisman (CSP `default-src 'self'`).
- Modelos `Usuario`, `Categoria`, `MetodoPago`, `Gasto`, `Presupuesto` y `Auditoria` según EDT 2.2, con `Gasto.campos_faltantes()` / `evaluar_completitud()` (RN-01, recálculo automático D-04) y `Presupuesto.estado()` (RN-05, RN-06).
- Migración inicial `0001` con las 6 tablas, restricciones CHECK y UNIQUE, índices parciales, 5 métodos de pago (RN-12) y 9 categorías plantilla con su color (RN-11).
- Comando `flask crear-admin` con política de contraseña de RF-03 y hash Argon2id (RNF-07).
- Ruta `/salud` para monitoreo de disponibilidad (RNF-13).
- Filtros Jinja2 `soles`, `fecha`, `fecha_corta`, `mes_anio` y `color_texto` (RNF-19, sección 11.1); fecha de hoy en America/Lima.
- Archivos de interfaz locales en `app/static/vendor/`: Bootstrap 5.3.3, Bootstrap Icons 1.11.3, Chart.js 4.4.9 e Inter 5.2.8.
- `wsgi.py`, `gunicorn.conf.py`, `.env.example`, `.gitattributes`.
- Pruebas con PostgreSQL de pruebas (89) e integración continua en GitHub Actions con `postgres:16`.

### Seguridad
- Sesión de 30 minutos renovada en cada petición, cookies `HttpOnly` y `SameSite=Lax` (`Secure` en producción), `ProxyFix` y HTTPS forzado solo en producción.
