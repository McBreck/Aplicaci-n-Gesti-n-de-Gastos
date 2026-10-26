# Historial de cambios

Todos los cambios relevantes de ControlGastos se registran en este archivo, agrupados por etapa de la EDT (fase 3.0 Implementación en adelante).

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Secciones por entrada: **Agregado**, **Cambiado**, **Corregido**, **Eliminado**, **Seguridad**.

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
