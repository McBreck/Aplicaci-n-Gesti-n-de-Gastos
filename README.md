# ControlGastos

Aplicación web para que los microemprendedores de Trujillo (panaderías, bodegas y negocios similares) registren y controlen sus **gastos** desde el celular. Incluye:

- registro con aviso de completitud;
- presupuesto mensual por categoría con alertas;
- análisis descriptivo y proyección al cierre de mes;
- recomendaciones;
- reportes en pantalla y en PDF.

Proyecto de tesis de la Universidad Privada Antenor Orrego (UPAO), Ingeniería de Computación y Sistemas:
*"Aplicación web con técnicas de análisis de datos para mejorar la gestión de gastos en micro emprendedores de Trujillo 2026"*.

- **Autores:** Ponce Vásquez, McBreck; Rivera Chamorro, Kristel Catherine.
- **Asesor:** Dr. Cieza Mostacero, Segundo Edwin.
- **Metodología:** cascada con retroalimentación en 7 fases.
- **Especificación completa:** [docs/especificacion/](docs/especificacion/).

## Requisitos

| Herramienta | Versión |
|---|---|
| Python | 3.11.x |
| PostgreSQL | 16.x (único motor admitido; SQLite está excluido) |
| Git | cualquier versión reciente |

Tecnología principal: Flask 3, SQLAlchemy 2, Alembic (Flask-Migrate), psycopg 3, Pandas, NumPy, ReportLab, Bootstrap 5.3.3, Chart.js 4.4 y Gunicorn (producción). Las versiones exactas están en `requirements.txt`.

## Instalación local (Windows)

1. Clona el repositorio y entra en la carpeta:
   ```powershell
   git clone <url-del-repositorio>
   cd Aplicaci-n-Gesti-n-de-Gastos
   ```
2. Crea y activa el entorno virtual con Python 3.11:
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   En bash: `python3.11 -m venv .venv && source .venv/bin/activate`
3. Instala las dependencias de desarrollo:
   ```powershell
   pip install -r requirements-dev.txt
   ```
4. Crea en PostgreSQL 16 el rol de la aplicación (sin privilegios de superusuario) y las bases de desarrollo y de pruebas. Cambia `CLAVE` por una contraseña propia:
   ```powershell
   psql -U postgres -h localhost -c "CREATE ROLE controlgastos LOGIN PASSWORD 'CLAVE' NOSUPERUSER NOCREATEDB NOCREATEROLE;"
   psql -U postgres -h localhost -c "ALTER ROLE controlgastos SET timezone = 'America/Lima';"
   psql -U postgres -h localhost -c "CREATE DATABASE controlgastos OWNER controlgastos ENCODING 'UTF8' TEMPLATE template0;"
   psql -U postgres -h localhost -c "CREATE DATABASE controlgastos_pruebas OWNER controlgastos ENCODING 'UTF8' TEMPLATE template0;"
   ```
   > ⚠️ Las pruebas **borran y recrean** la base de `TEST_DATABASE_URL`. Por seguridad, su nombre debe contener `prueba`.
5. Copia `.env.example` a `.env` y completa los valores (ver [Variables de entorno](#variables-de-entorno)):
   ```powershell
   Copy-Item .env.example .env
   ```
   En bash: `cp .env.example .env`
6. Aplica las migraciones y crea la cuenta de administrador:
   ```powershell
   flask db upgrade
   flask crear-admin
   ```
7. Inicia el servidor de desarrollo y abre http://127.0.0.1:5000:
   ```powershell
   flask run --debug
   ```
   Sin `--debug`, Flask guarda las plantillas en caché y no verás los cambios hasta reiniciar el servidor.
8. Ingresa con la cuenta de administrador y crea las cuentas de los microemprendedores desde **Usuarios**. Para recorrer la aplicación con datos de ejemplo, usa la [cuenta de demostración](#datos-de-demostración).

## Variables de entorno

| Variable | Para qué sirve | Ejemplo |
|---|---|---|
| `APP_ENV` | Entorno: `desarrollo`, `pruebas` o `produccion` | `desarrollo` |
| `SECRET_KEY` | Firma de la sesión y del token CSRF. Obligatoria; en producción, de 32 caracteres o más | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | Base de datos de la aplicación (solo PostgreSQL) | `postgresql+psycopg://controlgastos:CLAVE@localhost:5432/controlgastos` |
| `TEST_DATABASE_URL` | Base que usan las pruebas (se borra en cada ejecución) | `postgresql+psycopg://controlgastos:CLAVE@localhost:5432/controlgastos_pruebas` |
| `GUNICORN_BIND` | Dirección de Gunicorn (en producción, el socket de Nginx) | `127.0.0.1:8000` |

La aplicación no arranca si `DATABASE_URL` no es de PostgreSQL o si falta `SECRET_KEY`.

## Pantallas

| Pantalla | Ruta | Quién la usa |
|---|---|---|
| P-01 Inicio de sesión | `/login` | Todos |
| P-02 Dashboard | `/` | Microemprendedor |
| P-03 Registrar o editar gasto | `/gastos/nuevo` | Microemprendedor |
| P-04 Mis gastos | `/gastos` | Microemprendedor |
| P-05 Presupuesto | `/presupuesto` | Microemprendedor |
| P-06 Categorías | `/categorias` | Microemprendedor |
| P-07 Reportes (pantalla y PDF) | `/reportes` | Microemprendedor |
| P-08 Administración de usuarios | `/admin/usuarios` | Administrador |
| P-09 Mi cuenta | `/cuenta/contrasena` | Todos |

`/salud` responde `{"estado": "ok"}` sin datos, para el monitoreo de disponibilidad.

## Datos de demostración

```powershell
flask demo crear
```
Pide una contraseña (mínimo 8 caracteres, con letras y números) y crea la cuenta **PRUEBA Panadería** (`prueba.panaderia@controlgastos.test`) con:

- 60 días de gastos de una panadería hasta hoy, repartidos entre sus categorías y métodos de pago;
- algunos gastos incompletos (el dato que más falta es el método de pago);
- el presupuesto de cada mes del período, con montos justos para que se vean las alertas, la proyección y las recomendaciones.

Los montos salen de una semilla fija: con la misma fecha se generan siempre los mismos datos. Si la cuenta ya existe, el comando no cambia nada.

```powershell
flask demo borrar
```
Muestra las cuentas cuyo nombre empieza con `PRUEBA` y, si confirmas con `s`, las borra **por completo**: gastos, presupuestos, categorías y eventos de la bitácora. Las cuentas reales no se tocan. Con `--si` no pide confirmación.

> Los datos de prueba siempre llevan el prefijo `PRUEBA` y nunca se presentan como resultados de la investigación.

## Comandos

| Comando | Para qué sirve | Disponible desde |
|---|---|---|
| `flask db upgrade` | Aplica las migraciones a la base de datos | Etapa 1 |
| `flask db check` | Verifica que los modelos coinciden con las migraciones | Etapa 1 |
| `flask crear-admin` | Crea la cuenta de administrador | Etapa 1 |
| `flask run --debug` | Servidor de desarrollo | Etapa 1 |
| `pytest` | Ejecuta todas las pruebas (usa `TEST_DATABASE_URL`) | Etapa 1 |
| `pytest --cov=app/services` | Pruebas con cobertura de la capa de servicios | Etapa 1 |
| `flask demo crear` | Crea la cuenta "PRUEBA Panadería" con 60 días de gastos y presupuestos | Etapa 8 |
| `flask demo borrar` | Borra por completo las cuentas `PRUEBA` y todos sus datos (`--si` sin confirmar) | Etapa 8 |
| `flask demo rendimiento` | Genera 500 gastos `PRUEBA` en un mes (CP-28) | Etapa 9 |

## Pruebas y calidad

Las pruebas usan una base PostgreSQL propia (`TEST_DATABASE_URL`), que se borra y se recrea con la migración al empezar.

```powershell
pytest                                   # toda la suite
pytest --cov=app/services                # cobertura de los servicios (RNF-15: 70 % o más)
pytest tests/unit/test_demo.py -v        # un solo archivo, con el nombre de cada prueba
```

- `tests/unit/`: reglas de los servicios (una carpeta por capa, un archivo por servicio).
- `tests/integration/`: rutas, pantallas, API, seguridad y comandos de consola. Los nombres incluyen el caso de prueba (`test_cp26_...`).

**Estilo PEP 8 (RNF-15).** La configuración está en `setup.cfg` (líneas de hasta 120 caracteres). flake8 no forma parte de las dependencias del proyecto; instálalo aparte y ejecútalo desde la raíz:
```powershell
pip install flake8==7.4.1
python -m flake8
```
Sin mensajes significa que no hay observaciones.

## Estructura

```text
app/
├── __init__.py      create_app(): configuración, extensiones, seguridad y blueprints
├── cli.py           comandos crear-admin y demo
├── demo.py          datos de demostración PRUEBA
├── models/          entidades SQLAlchemy (usuario, categoría, método de pago, gasto, presupuesto, auditoría)
├── services/        reglas de negocio, análisis con Pandas, proyección con NumPy y PDF con ReportLab
├── blueprints/      rutas de cada módulo
├── templates/       pantallas Jinja2 y componentes
└── static/          estilos, scripts y librerías locales (vendor/)
migrations/          migraciones de Alembic
tests/               pruebas unitarias y de integración
docs/                especificación y registro de cambios de diseño
```

## Despliegue

Producción en un VPS Hostinger (Ubuntu 24.04, Nginx, Gunicorn, PostgreSQL 16, HTTPS con Let's Encrypt). La guía se escribirá en la Etapa 10, en `docs/DESPLIEGUE_HOSTINGER.md`.

## Historial de cambios

Ver [CHANGELOG.md](CHANGELOG.md).
