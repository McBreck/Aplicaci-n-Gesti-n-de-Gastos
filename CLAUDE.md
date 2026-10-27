# CLAUDE.md — ControlGastos

Instrucciones permanentes para cualquier sesión de Claude Code en este repositorio. La fuente de verdad completa está en `docs/especificacion/` (01 a 07): **léela al iniciar cada etapa**.

---

## Reglas que no se negocian (sección 0 de la especificación)

1. **Commits automáticos con autoría del usuario** (regla modificada por el usuario el 26/10/2026; reemplaza a "yo hago los commits a mano" de la especificación original).
   - Al cerrar cada etapa, Claude ejecuta `git add`, `git commit` (commits pequeños y coherentes) y `git push` de la rama de trabajo (`develop`), y luego se detiene.
   - El autor es siempre el usuario: `McBreck <mponcev4@upao.edu.pe>`, configurado con `git config --local` en este repositorio. Verificar `git config user.email` antes de cada commit.
   - Los mensajes **no llevan** `Co-Authored-By: Claude` ni ninguna otra atribución a Claude.
   - Claude NO ejecuta sin permiso explícito en ese momento: `git merge`, `git tag`, `git rebase`, `git reset`, `git stash`, `push --force` ni comandos destructivos (la fusión a `main` y la etiqueta de cada fase se piden en la compuerta).
2. **Trabajo por etapas, una por vez.** Cada etapa corresponde a un elemento de la EDT (`07_plan_implementacion.md`). Al terminar: ejecutar pruebas, entregar el cierre de etapa (sección 14) y **detenerse**. No empezar la siguiente hasta que el usuario escriba "continúa con la etapa N".
3. **No adelantar trabajo** de etapas posteriores ni agregar funciones fuera de la especificación. Si algo no está definido, preguntar antes de asumir.
4. **Si una petición contradice la especificación, avisar antes de hacerlo.**
5. **Antes de codificar algo no trivial**, explicar el enfoque en 3 a 5 líneas y continuar (sin esperar confirmación, salvo que haya una decisión del usuario).
6. Todo en **español**: interfaz, comentarios, docstrings, mensajes, documentación y mensajes de commit. Variables y funciones en español sin tildes (`registrar_gasto`, `es_completo`).
7. **Prohibido el vocabulario de Scrum** (sprint, backlog, historia de usuario, épica, scrum master, daily). Metodología: **cascada con retroalimentación en 7 fases**. Citas: `RF-nn`, `RNF-nn`, `CU-nn`, `CP-nn`, `RN-nn`.
8. **Prohibido SQLite** en cualquier entorno. Solo **PostgreSQL 16**.
9. **Prohibido capturar métricas de la investigación dentro de la app** (ECG, TRG, CRG se miden fuera, con fichas y cronómetro). Nada de tablas `metrica_evento`, cronómetros, tiempos de reporte ni campos "pretest/postest".
10. **Datos de prueba** siempre con el prefijo `PRUEBA`, nunca presentados como resultados, y con un comando para borrarlos por completo.
11. Comandos para **PowerShell** (Windows) y, si difieren, también para bash.
12. Código limpio: PEP 8, funciones cortas, sin lógica de negocio en las rutas (va en `services/`), sin SQL concatenado.

Formato de commit: `tipo(EDT): descripción` en español. Tipos: `feat`, `fix`, `test`, `docs`, `style`, `refactor`, `chore`, `ci`.
Ramas: trabajo diario en `develop`; fusión a `main` y etiqueta al cerrar cada fase.

---

## Resumen del proyecto (secciones 1 a 4)

### Contexto
- Tesis UPAO (Trujillo, Perú), Ingeniería de Computación y Sistemas: *"Aplicación web con técnicas de análisis de datos para mejorar la gestión de gastos en micro emprendedores de Trujillo 2026"*. Autores: Ponce Vásquez, McBreck; Rivera Chamorro, Kristel Catherine. Asesor: Dr. Cieza Mostacero, Segundo Edwin.
- Usuarios: microemprendedores con poca familiaridad técnica, principalmente en **celular**.
- La app **facilita** los indicadores ECG, TRG (< 1 s) y CRG, pero **no los mide**. El SUS se aplica fuera de la app.

### Alcance
- **Dentro:** acceso y cuentas, registro de gastos con completitud, consulta y filtros, categorías, presupuesto mensual por categoría, ejecutado vs. planificado, alertas, análisis descriptivo, proyección al cierre, recomendaciones por reglas, dashboard, reportes en pantalla y PDF, bitácora de auditoría.
- **Fuera (nunca):** ventas/ingresos, cuentas por cobrar/pagar, préstamos, inversiones, contabilidad, impuestos, facturación electrónica, inventario, nómina, métricas de la investigación, registro público de usuarios, recuperación de contraseña por correo.

### Tecnología (versiones fijas)
Python 3.11 · Flask 3.0.3 · SQLAlchemy 2 (estilo 2.0) · Flask-Migrate/Alembic · PostgreSQL 16 con psycopg 3 (`postgresql+psycopg://`) · Pandas 2.2.3 + NumPy 1.26.4 · Jinja2 · Bootstrap 5.3.3 · Bootstrap Icons 1.11.3 · Chart.js 4.4.x · ReportLab 4.2.5 · Gunicorn 22 (producción). Assets de terceros **locales** en `app/static/vendor/` (CSP `'self'`). `create_app()` se niega a arrancar si `DATABASE_URL` no empieza con `postgresql`. Zona horaria `America/Lima` con `zoneinfo`.

### Arquitectura
Tres capas, MVC + capa de servicios: Vista (Jinja2/Bootstrap/Chart.js) → Controladores (blueprints + Flask-WTF) → Servicios (reglas de negocio, Pandas, NumPy, ReportLab) → Modelo (SQLAlchemy 2, Alembic, PostgreSQL 16). Producción: Nginx → Gunicorn → Flask. Toda consulta filtra por `usuario_id = current_user.id`; id ajeno → **404**. Detalle de estructura, servicios y rutas en `docs/especificacion/03_arquitectura_y_datos.md`.

---

## Convenciones del código (establecidas en EDT 3.1 y 3.2)

- **Servicios** en `app/services/<nombre>.py` como funciones. El servicio hace el `commit`. Los errores de negocio llevan mensajes para el usuario:
  - con un solo campo: `ErrorUsuario(mensaje, campo=...)`;
  - con varios campos a la vez: `ErrorValidacion(errores)`, como en `gasto.py`.
  Los formularios Flask-WTF solo recogen datos y el token CSRF; la validación de negocio vive en el servicio.
- **Auditoría**: `auditoria.registrar(accion, entidad, ...)` agrega el evento sin hacer commit, para que se guarde junto con la operación. Nunca incluir contraseñas.
- **Acceso**: todas las rutas exigen sesión mediante el `before_request` global (`app/seguridad.py`). Los blueprints de microemprendedor usan `@bp.before_request` con `rol_requerido(ROL_MICROEMPRENDEDOR)`. Los datos propios se obtienen con `obtener_propio_o_404`.
- **Navegación**: un ítem del menú aparece solo cuando su endpoint existe. Endpoints previstos: `gastos.listar`, `gastos.nuevo` (también activa el FAB), `presupuesto.ver`, `categorias.listar`, `reportes.inicio` (`app/interfaz.py`).
- **Plantillas**: `base.html` (con sesión) y `base_publica.html` (sin sesión). Macros en `componentes/ui.html` y `componentes/formularios.html`.
- **Sin estilos ni scripts en línea** (CSP `'self'`). Los colores y anchos variables van en `data-cg-color`, `data-cg-color-texto` y `data-cg-ancho`, que aplica `static/js/app.js`. Una prueba revisa todas las plantillas.
- **Tablas**: usar `cg-tabla cg-tabla-apilable` con `data-etiqueta` en cada celda. Por debajo de 1200 px las filas se apilan como tarjetas (RNF-04).
- **Pruebas**:
  - fixtures en `tests/conftest.py`: `sesion`, `cliente`, `crear_usuario`, `crear_admin`, `crear_microemprendedor` (con sus categorías), `cargar_gastos`, `id_categoria` e `iniciar_sesion`;
  - los datos de verificación de la sección 9 están en `tests/datos_verificacion.py`; úsalos también en la EDT 3.5;
  - datos con el prefijo `PRUEBA`; la base de pruebas se borra y se recrea con la migración.
- **Listados**: una consulta para la página, otra para los agregados y otra para los totales por día (sin N+1). Siempre se filtra por `usuario_id` y `eliminado = FALSE`.
- **Presupuesto**: `presupuesto.comparar(usuario_id, mes)` es la única fuente de lo planificado y lo ejecutado por categoría (A7), de A9 y de las alertas. La usan P-05, el widget, la lista de categorías de la barra lateral y el badge.
  - La barra lateral la pide al dibujarse y la guarda en `g` una vez por petición (`app/interfaz.py`).
  - En la EDT 3.5, A7 y A9 sobre el DataFrame deben dar los mismos valores.
- **Analítica (EDT 3.5)**:
  - `analitica.construir_dataframe()` es la única consulta de gastos para el análisis; las métricas A1–A9 y S1 son funciones puras sobre el DataFrame;
  - `analitica.analizar_mes(usuario_id, mes, hoy)` reúne todo para el dashboard (P1 y R1–R7 incluidos) y recibe `hoy` como parámetro para que las pruebas no dependan del reloj;
  - las pruebas comprueban que A8 coincide con `gasto.resumir` y que A7/A9 coinciden con `presupuesto.comparar`.
- **Redondeo**: todo porcentaje pasa por `calculo.porcentaje_de` (decimal, "mitad hacia arriba", 1 decimal) y todo monto agregado por `calculo.a_soles`. Nunca uses `round()` directo para porcentajes que se muestran.
- **Utilidades compartidas**:
  - `services/validacion.py`: `interpretar_monto` (con `permitir_cero`) y `ErrorValidacion`;
  - `services/periodo.py`: `interpretar_mes(?mes=AAAA-MM)`, mes anterior y siguiente, último día;
  - macro `componentes/selector_mes.html`.
- **Dashboard y API (EDT 3.6)**:
  - las cifras se dibujan en el servidor;
  - los gráficos se piden a `/api/dashboard`, armados por `analitica.datos_graficos`;
  - toda ruta bajo `/api/` responde errores en JSON (401 sin sesión, 403, 404);
  - Chart.js se carga solo en páginas con gráficos (`{% block scripts %}`, RNF-02);
  - el JS de cada pantalla va en su propio archivo (`static/js/dashboard.js`), y los textos del usuario se escriben con `textContent`.
- **Reportes (EDT 3.7)**:
  - `reporte.interpretar_solicitud(request.args, hoy)` devuelve la `SolicitudReporte`, y `como_argumentos()` rearma su URL (de la pantalla al PDF);
  - `reporte.generar` usa `analitica.construir_dataframe`, la misma fuente que el dashboard;
  - el PDF se arma en memoria y nunca se guarda en el servidor; el texto del usuario pasa por `escape()` antes de llegar a ReportLab;
  - la tabla del reporte no es apilable: es compacta y, en el celular, la cantidad pasa bajo el grupo;
  - en las pruebas, el texto del PDF se lee con `tests/utilidades_pdf.texto_pdf`.
- **Datos de demostración (EDT 3.8 y 4.4)**:
  - `app/demo.py` no es un servicio de negocio: arma datos PRUEBA para demostraciones y pruebas;
  - `planificar_gastos(hoy)` y `planificar_rendimiento(mes, hoy)` son funciones puras y reproducibles (semilla fija);
  - `crear()` y `crear_rendimiento()` guardan todo en una transacción; `borrar()` elimina las cuentas PRUEBA por completo.
- **Estilo**: `python -m flake8` desde la raíz, con la configuración de `setup.cfg` (PEP 8, líneas de hasta 120 caracteres). La integración continua también lo ejecuta. Cada servicio tiene su archivo de pruebas en `tests/unit/`.
- **Pruebas de la fase 4.0**:
  - las listas de verificación están en `docs/pruebas/` (4.2, 4.4, 4.5, 4.6 y la plantilla DEF-nn);
  - las pruebas de cada caso se llaman `test_cpNN_...` y se ejecutan con `pytest -k cpNN -v`;
  - `tests/test_trazabilidad.py` exige al menos una prueba para cada caso entre CP-01 y CP-32;
  - si cambia un mensaje o una pantalla, actualiza también su lista de verificación;
  - un defecto se corrige con `fix(4.x): … (DEF-nn)`.
- **Despliegue (EDT 5.1–5.3)**:
  - todo vive en `deploy/` y la guía es `docs/DESPLIEGUE_HOSTINGER.md`. Claude **nunca** ejecuta nada en un servidor real: el despliegue se hace con el usuario;
  - los scripts bash usan `set -euo pipefail`, ponen todo dentro de `main()` y deben pasar shellcheck (lo revisa el CI);
  - `.gitattributes` fuerza LF: un script con CRLF falla en Ubuntu;
  - en el VPS:
    - el código pertenece a root en `/srv/controlgastos`;
    - el servicio corre como `controlgastos` con el grupo `www-data` (para el socket) y `controlgastos` como grupo adicional (para leer `.env`, 640 root:controlgastos);
  - si cambia algo del despliegue, actualiza también la guía y vuelve a ensayarlo en Ubuntu 24.04 (WSL).
- **Servidor de desarrollo**: `flask run --debug`. Sin `--debug`, las plantillas quedan en caché.

## Decisiones confirmadas por los investigadores (26/10/2026)

- **Versiones indirectas fijas** en `requirements.txt`: SQLAlchemy 2.1.6, alembic 1.20.1 y limits 5.8.0.
- **Casos de prueba**: catálogo propuesto y confirmado (los nombres de las pruebas usan estos códigos):

  | CP | Qué cubre |
  |---|---|
  | CP-01 | Ingreso válido |
  | CP-02 | Datos incorrectos |
  | CP-03 | Bloqueo tras 5 intentos |
  | CP-04 | Cuenta desactivada |
  | CP-05 | Cierre de sesión |
  | CP-06 | Cierre por inactividad |
  | CP-07 | Cambio de contraseña |
  | CP-08 | Alta de cuenta |
  | CP-09 | Duplicado, edición, estado y restablecimiento |
  | CP-10 | Registro completo |
  | CP-11 | Registro solo con fecha y monto |
  | CP-12 | Monto inválido |
  | CP-13 | Fecha futura |
  | CP-14 | Completar al editar |
  | CP-15 | Eliminar |
  | CP-16 | Filtros y paginación |
  | CP-17 | Completitud y dato más omitido |
  | CP-18 | Crear y renombrar categorías |
  | CP-19 | Desactivar categoría |
  | CP-20 | Presupuesto y copia del mes anterior |
  | CP-21 | Comparación y alertas (límites 79.9, 80, 100 y 100.1 %) |
  | CP-22 | Los cuatro KPI del dashboard coinciden con el listado del mismo período |
  | CP-23 | Datos de los gráficos (`/api/dashboard`): solo del usuario y coherentes con el total |
  | CP-24 | Proyección (o "Datos insuficientes") y recomendaciones con acción |
  | CP-25 | Estados especiales (mes sin gastos, sin presupuesto, error de gráficos), tarjetas rápidas y actividad |
  | CP-26 | Reporte en pantalla: los cuatro tipos de período, las tres agrupaciones, total = suma del período, período sin gastos y solo datos del usuario |
  | CP-27 | PDF: nombre del archivo, mismos datos que la pantalla y error al generarlo |
  | CP-29 | Control de acceso (403 y 404) |
  | CP-30 | CSRF |
  | CP-31 | Contraseñas protegidas |

  CP-28 y CP-32 a CP-34 están propuestos en la etapa 9 (sección siguiente).
- **Detalles aprobados**:
  - P-08 solo gestiona cuentas de microemprendedor; las de administrador se crean con `flask crear-admin`;
  - la contraseña nueva debe ser distinta de la actual;
  - en P-08, "Desactivar" y "Restablecer" van en el menú "Más acciones";
  - los filtros de gastos incluyen "Sin categoría" y "Sin registrar";
  - la búsqueda no distingue tildes ni mayúsculas;
  - si "Desde" es posterior a "Hasta", las fechas se intercambian con un aviso;
  - "Copiar del mes anterior" reemplaza solo las categorías que coinciden, conserva las demás y no copia categorías inactivas;
  - los gastos sin categoría no cuentan en A9 (P-05 lo aclara con una nota);
  - el presupuesto se edita entre 2026-01 y 2100-12; los demás meses son de solo lectura;
  - cada categoría de la barra lateral abre Mis gastos filtrado por ella.
- **Recomendaciones (confirmadas tras la EDT 3.5)**:
  - R2 muestra el exceso en soles y en % sobre lo planificado ("en S/ 30.30 (5.8 %)");
  - R3 y R6 solo aplican al mes en curso;
  - "Sin categoría" no genera R5 ni R7;
  - en empates gana la prioridad, luego el orden de la tabla (R5 antes que R7) y luego el valor más alto.
- **Dashboard (confirmado tras la EDT 3.6)**:
  - las tarjetas rápidas se eligen por cantidad de registros en los últimos 30 días y muestran el monto del mes; el "+" elige la categoría en el registro rápido y, sin JavaScript, abre P-03 con la categoría marcada;
  - el selector de mes no permite meses futuros;
  - en un mes anterior, la actividad reciente muestra los últimos 7 días hasta el corte de ese mes.
- **Reportes (confirmado tras la EDT 3.7)**:
  - la semana va de lunes a domingo y contiene la fecha elegida (igual que el gráfico semanal);
  - el mensual ofrece los últimos 24 meses; para fechas más antiguas se usa Personalizado;
  - por categoría y por método, las filas van de mayor a menor total ("Sin categoría" y "Sin registrar" son un grupo más); por fecha, solo los días con gastos, del más antiguo al más reciente;
  - el PDF es A4 vertical, con la agrupación y el número de página; si el usuario no tiene nombre de negocio, va su nombre;
  - en un período sin gastos no se ofrece el botón de PDF;
  - en el celular la cantidad va bajo el nombre del grupo ("2 gastos") y se oculta su columna, para que la tabla quepa en 320 px.
- **Demostración y estilo (confirmado tras la EDT 3.8)**:
  - cuenta "PRUEBA Panadería" (`prueba.panaderia@controlgastos.test`), con la contraseña elegida al crearla, 60 días hasta hoy con semilla fija, cerca del 20 % de gastos incompletos (el método de pago es el más omitido) y el presupuesto de cada mes desde enero de 2026;
  - "Otros" queda sin presupuesto y Transporte tiene un monto bajo a propósito, para que se vean Excedida y las recomendaciones;
  - `flask demo borrar` borra todas las cuentas cuyo nombre empieza con "PRUEBA" (también las de administrador), con sus gastos, presupuestos, categorías y bitácora; pide confirmación (s/n) salvo con `--si`;
  - PEP 8 con líneas de hasta 120 caracteres; `flake8==7.4.1` está en `requirements-dev.txt` (cambio aceptado sobre la especificación) y se ejecuta en el CI.

## Propuesto en la etapa 9, EDT 4.1–4.7 (pendiente de confirmación)

- **Casos de prueba**:

  | CP | Qué cubre |
  |---|---|
  | CP-28 | Reporte de un mes con 500 gastos en menos de 1 s: promedio de 10 mediciones con cronómetro |
  | CP-32 | HTTPS con redirección 301 desde HTTP (en el servidor, después de la EDT 5.3) |
  | CP-33 | Diseño responsivo sin desplazamiento horizontal desde 360 px en Chrome, Edge, Firefox y Chrome Android |
  | CP-34 | Usabilidad con el cuestionario SUS (meta ≥ 68), aplicado fuera de la app |

- **`flask demo rendimiento`**:
  - cuenta "PRUEBA Rendimiento" (`prueba.rendimiento@controlgastos.test`), sin presupuesto, con 500 gastos en el mes anterior (o el de `--mes AAAA-MM`, nunca futuro);
  - los gastos fijos caen en su día y el resto son compras variables repartidas entre todos los días.
- **Redirección a HTTPS**: la aplicación también redirige con 301 (además de Nginx), para cumplir RNF-08 aunque una petición llegue por HTTP.
- **Fase 4.0**: no se definieron nombres para 4.1, 4.3 ni 4.7; `docs/pruebas/` cubre 4.2, 4.4, 4.5 y 4.6, como indica el plan.

## Propuesto en la etapa 10, EDT 5.1–5.3 (pendiente de confirmación)

- **Repositorio privado**: el VPS descarga el código con una llave de despliegue de solo lectura para root.
- **Orden de la guía**:
  - en 5.1 los scripts se copian con `scp` (el `git clone` es en 5.3);
  - el cron del respaldo se instala en 5.3.7, cuando ya está el código;
  - la restauración con datos se repite en 5.3.9.
- **Permisos en el VPS**:
  - el código es de root y la aplicación solo lo lee;
  - `.env` es 640 root:controlgastos;
  - el socket queda en `/run/controlgastos` (controlgastos:www-data, `umask` 007).
- **`desplegar.sh`**: despliega `main` y hace un respaldo antes de migrar.
- **GitHub Actions**: el workflow solo corre con la variable `DESPLIEGUE_HABILITADO=si` y entra con un usuario `despliegue` que solo puede ejecutar `desplegar.sh` con sudo.
- **Python 3.11**: el PPA deadsnakes por defecto; uv 0.6.0 como alternativa (Python en `/opt/uv-python`).
- **Administrador real**: sin el prefijo PRUEBA, para que `flask demo borrar` nunca lo elimine.

## Entorno local (Windows)
- Python 3.11.9 instalado junto a 3.12: usar `py -3.11` para crear el venv (`py -3.11 -m venv .venv`).
- PostgreSQL 16.15 como servicio `postgresql-x64-16`, puerto 5432, binarios en `C:\Program Files\PostgreSQL\16\bin`. La contraseña del superusuario está fuera del repositorio, en `%USERPROFILE%\controlgastos_postgres.txt`.
- Gunicorn no funciona en Windows. El despliegue se ensayó en WSL 2 con Ubuntu 24.04 (instalador, systemd, Nginx con HTTPS autofirmado, respaldo y restauración, reinicio automático) y luego se borró la distribución.
  - Para volver a ensayarlo: `wsl --install Ubuntu-24.04 --no-launch` y ejecutar los comandos como root con `wsl -d Ubuntu-24.04 -u root -- bash script.sh`.
  - Los scripts de ensayo se escriben en archivos `.sh`: PowerShell interpreta `$(...)` dentro de las comillas.
