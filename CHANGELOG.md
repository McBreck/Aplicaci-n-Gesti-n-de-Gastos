# Historial de cambios

Todos los cambios relevantes de ControlGastos se registran en este archivo, agrupados por etapa de la EDT (fase 3.0 Implementación en adelante).

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Secciones por entrada: **Agregado**, **Cambiado**, **Corregido**, **Eliminado**, **Seguridad**.

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
