# 07 — Plan de implementación, despliegue y cierre de etapas

> Fuente: prompt maestro de implementación, secciones 12, 13 y 14.

## 12. Plan de implementación por etapas (EDT)

> Los nombres de 3.1 a 3.7 son la propuesta para mi EDT; 3.8 = pruebas unitarias, 4.1–4.7 = pruebas y 5.1–5.3 = despliegue están confirmados. Úsalos en los mensajes de commit.

**Ramas:** trabajo diario en `develop`. Al cerrar cada fase (compuerta) te pediré los comandos para fusionar en `main` y etiquetar.

| Etapa | EDT | Contenido | Pruebas mínimas al cerrar |
|---|---|---|---|
| 0 | — | Sección 0 "Tu primera respuesta" | — |
| 1 | 3.1 Entorno, estructura y base de datos | `create_app`, configuración por entorno con `.env` (`APP_ENV`, `SECRET_KEY`, `DATABASE_URL`, `TEST_DATABASE_URL`), extensiones, modelos, migración inicial con datos de catálogo, `wsgi.py`, `gunicorn.conf.py` (bind local en desarrollo), assets en `static/vendor/`, comando `flask crear-admin`, ruta `/salud`, filtros de formato, `conftest.py` con PostgreSQL de pruebas, CI en `.github/workflows/ci.yml` (servicio `postgres:16`, `pip install -r requirements-dev.txt`, `flask db upgrade`, `pytest --cov=app/services`) | La app se niega a arrancar con una URL no PostgreSQL; la migración crea 6 tablas, 5 métodos y 9 categorías plantilla; restricciones CHECK y UNIQUE rechazan datos inválidos |
| 2 | 3.2 Acceso, administración e interfaz base | `base.html` con todo el sistema de diseño de la sección 11 (barra lateral, cabecera, offcanvas, toasts, macros, páginas de error), P-01, P-08, P-09, AuthService, UsuarioService (copia de categorías al crear cuenta), AuditoriaService, seguridad de la sección 10, `CR-01` | CP-01 a CP-09, CP-29 (rutas admin), CP-30, CP-31 |
| 3 | 3.3 Gastos y completitud | P-03, registro rápido (componente), P-04, GastoService (registrar, modificar, eliminar lógico, listar con filtros, completitud A8), componente `actividad` | CP-10 a CP-17, CP-29 (gasto ajeno → 404) |
| 4 | 3.4 Categorías, presupuesto y alertas | P-06, P-05, CategoriaService, PresupuestoService (guardar, copiar, comparar, estados), barra lateral con categorías y montos, widget de presupuesto, badge de alertas | CP-18 a CP-21; límites 79.9/80/100/100.1 % |
| 5 | 3.5 Analítica, proyección y recomendaciones | AnaliticaService (A1–A9, S1), ProyeccionService (P1), RecomendacionService (R1–R7) como funciones puras + construcción del DataFrame | Todos los valores de verificación de la sección 9 |
| 6 | 3.6 Dashboard | P-02 completo, `/api/dashboard`, `dashboard.js`, tarjetas rápidas, gráfico semanal, acumulado, método de pago, estados especiales | CP-22 a CP-25; el JSON solo contiene datos del usuario |
| 7 | 3.7 Reportes y PDF | P-07, ReporteService (diario, semanal, mensual, personalizado; agrupación por categoría, método o fecha; totales y subtotales), PDF A4 con ReportLab (negocio, título "Reporte de gastos", período, tabla, total, fecha de emisión en America/Lima, pie "Generado por ControlGastos"), nombre `reporte_gastos_AAAAMMDD_AAAAMMDD.pdf` | CP-26, CP-27; reporte de 500 gastos generado en < 1 s en una prueba automatizada orientativa |
| 8 | 3.8 Pruebas unitarias y cierre de la fase 3.0 | Completar pruebas unitarias de todos los servicios, cobertura ≥ 70 % en `app/services`, comandos `flask demo crear` (cuenta "PRUEBA Panadería" con 60 días de gastos variados, algunos incompletos, y presupuestos), `flask demo borrar`, README actualizado, `CHANGELOG.md`, verificación PEP 8 | `pytest --cov=app/services` ≥ 70 %; toda la suite en verde |
| 9 | 4.1–4.7 Soporte a la fase de pruebas | Pruebas de integración automatizadas para CP-01 a CP-27 que sean automatizables; `flask demo rendimiento` (500 gastos PRUEBA en un mes para CP-28); `docs/pruebas/` con listas de verificación para 4.2 funcionales, 4.4 rendimiento (procedimiento de cronometraje manual, 10 repeticiones), 4.5 seguridad (CP-29 a CP-32 y revisión OWASP), 4.6 responsivo y SUS (CP-33, CP-34; el SUS se aplica fuera de la app) y plantilla de defectos DEF-nn | Suite completa en verde |
| 10 | 5.1–5.3 Preparación del despliegue en Hostinger | Sección 13 (archivos listos, sin ejecutar nada en ningún servidor) | `APP_ENV=produccion` arranca con Gunicorn en local contra PostgreSQL y exige `SECRET_KEY` |

## 13. Dejar listo el despliegue en Hostinger (Etapa 10; lo ejecutaremos juntos otro día)

Arquitectura de producción aprobada: VPS Hostinger **KVM 1** (1 vCPU, 4 GB RAM, 50 GB NVMe) con **Ubuntu 24.04 LTS**; PostgreSQL 16 solo en localhost con usuario de aplicación sin privilegios de superusuario; Nginx como proxy inverso con HTTPS de Let's Encrypt y redirección 301; Gunicorn con 3 workers bajo systemd por socket Unix; UFW con 22 (solo llave SSH), 80 y 443; respaldo diario con pg_dump y 7 copias; dominio propio apuntando al VPS (registro A). El alojamiento compartido de Hostinger no sirve porque no admite PostgreSQL.

Crea, sin ejecutar nada remoto:
- `deploy/nginx/controlgastos.conf` (plantilla con `DOMINIO`): `server_name DOMINIO www.DOMINIO`, `location /static/` con `alias` y caché de 7 días, `proxy_pass http://unix:/run/controlgastos/gunicorn.sock`, cabeceras `X-Forwarded-For` y `X-Forwarded-Proto`, `client_max_body_size 1m`, gzip, cabeceras de seguridad. Certbot agregará el bloque 443 y la redirección.
- `deploy/systemd/controlgastos.service`: usuario `controlgastos`, `WorkingDirectory=/srv/controlgastos`, `EnvironmentFile=/srv/controlgastos/.env`, `RuntimeDirectory=controlgastos`, `ExecStart=/srv/controlgastos/venv/bin/gunicorn -c gunicorn.conf.py wsgi:app`, `Restart=always`.
- `gunicorn.conf.py` que lea `GUNICORN_BIND` (socket en producción, `127.0.0.1:8000` por defecto), 3 workers, timeout 30, logs a stdout.
- `deploy/scripts/instalar_servidor.sh` (comentado paso a paso, idempotente): actualización, zona horaria America/Lima, usuario, UFW, PostgreSQL 16 (es el paquete por defecto de Ubuntu 24.04), **Python 3.11** (Ubuntu 24.04 trae 3.12: instalar 3.11 con el PPA deadsnakes o con `uv`; deja ambas opciones y la verificación), Nginx, Certbot.
- `deploy/scripts/desplegar.sh`: `git pull`, `pip install -r requirements.txt`, `flask db upgrade`, `systemctl restart controlgastos`, prueba de `/salud`.
- `deploy/scripts/respaldo_bd.sh` + línea de cron (02:30 diario), `pg_dump -Fc`, conserva 7 archivos, y `deploy/scripts/restaurar_bd.sh` para la prueba de restauración.
- `.github/workflows/deploy.yml` **solo con `workflow_dispatch`** (manual), por SSH con secretos `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`, que ejecuta `desplegar.sh`. Desactivado hasta la EDT 5.3.
- `.env.example` de producción comentado (`APP_ENV=produccion`, `SECRET_KEY`, `DATABASE_URL=postgresql+psycopg://controlgastos:CLAVE@localhost:5432/controlgastos`, `GUNICORN_BIND=unix:/run/controlgastos/gunicorn.sock`).
- `docs/DESPLIEGUE_HOSTINGER.md`: guía en español para un principiante, dividida en **5.1 Servidor VPS** (contratar KVM 1, elegir Ubuntu 24.04 sin panel, llave SSH, primer acceso, usuario, UFW), **5.2 Base de datos** (PostgreSQL, rol y base, `listen_addresses = 'localhost'`, respaldo y restauración de prueba), **5.3 Publicación con HTTPS** (DNS del dominio en Hostinger con registro A, clonar el repositorio, venv 3.11, `.env`, migraciones, `flask crear-admin`, systemd, Nginx, `certbot --nginx -d DOMINIO -d www.DOMINIO`, renovación automática, verificación de CP-32 con `curl -I http://DOMINIO` → 301 y certificado válido) y una sección de **evidencias para capturar** en cada paso (para mi documento de EDT). Incluye solución de problemas frecuentes (502 Bad Gateway, permisos del socket, migraciones, zona horaria).

## 14. Formato obligatorio del cierre de cada etapa

Al terminar cada etapa entrégame, en este orden:
1. **Resumen** (3 a 6 viñetas) de lo implementado y su trazabilidad (`RF`, `CU`, `RN`, `CP`).
2. **Archivos** creados o modificados.
3. **Cómo probarlo** en mi computadora (comandos PowerShell y qué pantalla abrir).
4. **Resultado de las pruebas** (`pytest` con el resumen y, desde la etapa 5, la cobertura de `app/services`).
5. **Entrada para `CHANGELOG.md`** (ya escrita por ti en el archivo).
6. **Commits sugeridos**: uno o varios commits pequeños y coherentes, en formato `tipo(EDT): descripción` en español, por ejemplo:
   ```
   git add app/models migrations
   git commit -m "feat(3.1): modelos de datos y migración inicial con catálogos"
   git add tests
   git commit -m "test(3.1): restricciones del esquema en PostgreSQL"
   ```
   Tipos: `feat`, `fix`, `test`, `docs`, `style`, `refactor`, `chore`, `ci`. En el cierre de fase, además, los comandos de fusión y etiqueta (por ejemplo `git tag -a fase-3.0 -m "Compuerta de la fase 3.0 Implementación"`).
7. **Pendientes o decisiones** que necesito tomar (si las hay).
8. La frase: **"Etapa N terminada. Escribe «continúa con la etapa N+1» cuando hayas hecho los commits."** y te detienes.
