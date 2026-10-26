# Historial de cambios

Todos los cambios relevantes de ControlGastos se registran en este archivo, agrupados por etapa de la EDT (fase 3.0 Implementación en adelante).

El formato se basa en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Secciones por entrada: **Agregado**, **Cambiado**, **Corregido**, **Eliminado**, **Seguridad**.

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
