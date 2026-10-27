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
  | CP-29 | Control de acceso (403 y 404) |
  | CP-30 | CSRF |
  | CP-31 | Contraseñas protegidas |

  CP-22 a CP-28 y CP-32 a CP-34 se definen en sus etapas.
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

## Propuesto en la EDT 3.6 (pendiente de confirmación)

- **Casos de prueba**:

  | CP | Qué cubre |
  |---|---|
  | CP-22 | Los cuatro KPI del dashboard coinciden con el listado del mismo período |
  | CP-23 | Datos de los gráficos (`/api/dashboard`): solo del usuario y coherentes con el total |
  | CP-24 | Proyección (o "Datos insuficientes") y recomendaciones con acción |
  | CP-25 | Estados especiales (mes sin gastos, sin presupuesto, error de gráficos), tarjetas rápidas y actividad |
- **Tarjetas rápidas**: se eligen por cantidad de registros en los últimos 30 días y muestran el monto del mes. El "+" elige la categoría en el registro rápido; sin JavaScript abre P-03 con la categoría marcada.
- **Dashboard de otro mes**: el selector no permite meses futuros. La actividad reciente muestra los últimos 7 días hasta el corte del mes elegido.

## Entorno local (Windows)
- Python 3.11.9 instalado junto a 3.12: usar `py -3.11` para crear el venv (`py -3.11 -m venv .venv`).
- PostgreSQL 16.15 como servicio `postgresql-x64-16`, puerto 5432, binarios en `C:\Program Files\PostgreSQL\16\bin`. La contraseña del superusuario está fuera del repositorio, en `%USERPROFILE%\controlgastos_postgres.txt`.
