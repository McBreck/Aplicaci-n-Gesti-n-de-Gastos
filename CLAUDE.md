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

## Entorno local (Windows)
- Python 3.11.9 instalado junto a 3.12: usar `py -3.11` para crear el venv (`py -3.11 -m venv .venv`).
- PostgreSQL 16.15 como servicio `postgresql-x64-16`, puerto 5432, binarios en `C:\Program Files\PostgreSQL\16\bin`. La contraseña del superusuario está fuera del repositorio, en `%USERPROFILE%\controlgastos_postgres.txt`.
