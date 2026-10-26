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

> La estructura de la aplicación se crea en la Etapa 1 (EDT 3.1). Los pasos de abajo funcionarán desde esa etapa.

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
4. Crea las bases de datos de desarrollo y de pruebas en PostgreSQL 16:
   ```powershell
   psql -U postgres -h localhost -c "CREATE DATABASE controlgastos;"
   psql -U postgres -h localhost -c "CREATE DATABASE controlgastos_pruebas;"
   ```
5. Copia `.env.example` a `.env` y completa `SECRET_KEY`, `DATABASE_URL` y `TEST_DATABASE_URL`:
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
   flask run
   ```

## Comandos

| Comando | Para qué sirve | Disponible desde |
|---|---|---|
| `flask db upgrade` | Aplica las migraciones a la base de datos | Etapa 1 |
| `flask crear-admin` | Crea la cuenta de administrador | Etapa 1 |
| `flask run` | Servidor de desarrollo | Etapa 1 |
| `pytest` | Ejecuta todas las pruebas (usa `TEST_DATABASE_URL`) | Etapa 1 |
| `pytest --cov=app/services` | Pruebas con cobertura de la capa de servicios | Etapa 1 |
| `flask demo crear` | Crea la cuenta "PRUEBA Panadería" con datos de prueba | Etapa 8 |
| `flask demo borrar` | Borra por completo todos los datos `PRUEBA` | Etapa 8 |
| `flask demo rendimiento` | Genera 500 gastos `PRUEBA` en un mes (CP-28) | Etapa 9 |

> Los datos de prueba siempre llevan el prefijo `PRUEBA` y nunca se presentan como resultados de la investigación.

## Despliegue

Producción en un VPS Hostinger (Ubuntu 24.04, Nginx, Gunicorn, PostgreSQL 16, HTTPS con Let's Encrypt). La guía se escribirá en la Etapa 10, en `docs/DESPLIEGUE_HOSTINGER.md`.

## Historial de cambios

Ver [CHANGELOG.md](CHANGELOG.md).
