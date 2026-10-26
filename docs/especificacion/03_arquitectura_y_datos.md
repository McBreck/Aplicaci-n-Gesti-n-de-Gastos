# 03 — Tecnología, arquitectura y modelo de datos

> Fuente: prompt maestro de implementación, secciones 3, 4 y 5 (EDT 2.1 y 2.2).

## 3. Tecnología obligatoria (versiones fijas)

`requirements.txt`:
```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.7
Flask-Login==0.6.3
Flask-WTF==1.2.1
Flask-Limiter==3.8.0
flask-talisman==1.1.0
argon2-cffi==23.1.0
psycopg[binary]==3.2.3
pandas==2.2.3
numpy==1.26.4
reportlab==4.2.5
python-dotenv==1.0.1
gunicorn==22.0.0
```
`requirements-dev.txt`: `-r requirements.txt`, `pytest==8.3.3`, `pytest-cov==5.0.0`.

- Python 3.11 · Flask 3 · SQLAlchemy 2 (estilo 2.0: `select()`, `Mapped[]`, `mapped_column`) · Alembic vía Flask-Migrate · PostgreSQL 16 con el controlador psycopg 3 (`postgresql+psycopg://`) · Pandas + NumPy · Jinja2 · Bootstrap 5.3.3 · Bootstrap Icons 1.11.3 · Chart.js 4.4.x · ReportLab · Gunicorn (producción).
- Archivos de interfaz de terceros **descargados en `app/static/vendor/`** con versión exacta (Bootstrap CSS y JS bundle, Bootstrap Icons, Chart.js UMD, fuente Inter en woff2). Nada desde CDN, para que la política CSP sea `'self'`. Si no puedes descargar algún archivo, dime cuál y de dónde lo bajo yo.
- `create_app()` debe **negarse a arrancar** si `DATABASE_URL` no empieza con `postgresql` (mensaje claro en español).
- Zona horaria de la aplicación: `America/Lima` (usa `zoneinfo`). Toda "fecha de hoy" se calcula en esa zona.

## 4. Arquitectura (aprobada en EDT 2.1)

Tres capas con patrón MVC + capa de servicios:

| Capa | Rol MVC | Tecnología | Responsabilidad |
|---|---|---|---|
| Presentación | Vista | Jinja2, Bootstrap 5, Chart.js 4, JS mínimo | Páginas HTML, interfaz responsiva, gráficos |
| Negocio – controladores | Controlador | Blueprints de Flask, Flask-WTF | Recibir peticiones, validar formularios, invocar servicios, elegir la vista |
| Negocio – servicios | (apoyo) | Python 3.11, Pandas, NumPy, ReportLab | Reglas de negocio, análisis, proyección, recomendaciones, reportes |
| Datos | Modelo | SQLAlchemy 2, Alembic, PostgreSQL 16 | Entidades, relaciones, restricciones, persistencia |

Flujo: Navegador → (HTTPS) → Nginx → Gunicorn → Flask (Vista ⇄ Controlador → Servicios → Modelo) → psycopg 3 → PostgreSQL 16. Nginx sirve `/static`. La Vista recibe HTML con `render_template` y datos de gráficos por `fetch` a la API JSON.

### Estructura del código
```
controlgastos/                 (raíz del repositorio)
├── app/
│   ├── __init__.py            # create_app(): fábrica, registra extensiones, blueprints, filtros y comandos CLI
│   ├── config.py              # Config base, Desarrollo, Pruebas, Produccion (según APP_ENV)
│   ├── extensions.py          # db, migrate, login_manager, csrf, limiter, talisman
│   ├── models/                # usuario.py, categoria.py, metodo_pago.py, gasto.py, presupuesto.py, auditoria.py
│   ├── services/              # auth, usuario, gasto, categoria, presupuesto, analitica, proyeccion,
│   │                          # recomendacion, reporte, auditoria  (+ formato.py para soles/fechas)
│   ├── blueprints/            # auth, admin, gastos, categorias, presupuesto, dashboard, reportes
│   ├── forms/                 # formularios Flask-WTF
│   ├── cli.py                 # comandos: crear-admin, demo crear/borrar/rendimiento
│   ├── templates/             # base.html, componentes/ y una carpeta por blueprint
│   └── static/                # css/app.css, js/*.js, img/, vendor/
├── migrations/                # Alembic
├── tests/
│   ├── conftest.py            # app de pruebas con TEST_DATABASE_URL (PostgreSQL)
│   ├── unit/                  # servicios
│   └── integration/           # rutas con el cliente de pruebas de Flask
├── deploy/                    # nginx, systemd, scripts (etapa 5)
├── docs/                      # especificacion/, cambios/, pruebas/, DESPLIEGUE_HOSTINGER.md
├── .github/workflows/ci.yml
├── .env.example
├── gunicorn.conf.py
├── requirements.txt / requirements-dev.txt
└── wsgi.py
```

### Servicios
| Servicio | Responsabilidad | Requisitos |
|---|---|---|
| AuthService | Autenticar, intentos fallidos y bloqueo, cambiar contraseña | RF-01 a RF-03, RNF-11 |
| UsuarioService | Crear y mantener cuentas; copiar categorías predeterminadas a cada cuenta nueva | RF-04 |
| GastoService | Registrar, modificar, eliminar (lógico), listar con filtros; evaluar y resumir completitud | RF-05 a RF-10 |
| CategoriaService | Categorías predeterminadas y propias | RF-11 |
| PresupuestoService | Guardar y copiar presupuestos; comparar ejecutado vs. planificado; estados | RF-12 a RF-14 |
| AnaliticaService | DataFrame del período y métricas A1–A9 con Pandas | RF-15, RF-16 |
| ProyeccionService | Proyección P1 por regresión lineal con NumPy | RF-17 |
| RecomendacionService | Reglas R1–R7, máximo tres | RF-18 |
| ReporteService | Reporte agrupado y exportación PDF (ReportLab) | RF-19, RF-20 |
| AuditoriaService | Registrar eventos en la bitácora | RNF-12 |

### Rutas (catálogo aprobado)
| Blueprint | Método | Ruta | Función | Requisitos |
|---|---|---|---|---|
| auth | GET, POST | /login | Inicio de sesión | RF-01 |
| auth | POST | /logout | Cierre de sesión | RF-02 |
| auth | GET, POST | /cuenta/contrasena | Mi cuenta y cambio de contraseña | RF-03 |
| admin | GET | /admin/usuarios | Listado de cuentas | RF-04 |
| admin | GET, POST | /admin/usuarios/nuevo | Alta de cuenta | RF-04 |
| admin | GET, POST | /admin/usuarios/<id>/editar | Edición | RF-04 |
| admin | POST | /admin/usuarios/<id>/estado | Activar/desactivar | RF-04 |
| admin | POST | /admin/usuarios/<id>/restablecer | Contraseña temporal | RF-04 |
| gastos | GET | /gastos | Listado con filtros y completitud | RF-09, RF-10 |
| gastos | GET, POST | /gastos/nuevo | Registro | RF-05, RF-06 |
| gastos | GET, POST | /gastos/<id>/editar | Modificación | RF-07, RF-06 |
| gastos | POST | /gastos/<id>/eliminar | Eliminación lógica | RF-08 |
| categorias | GET, POST | /categorias | Listado y creación | RF-11 |
| categorias | POST | /categorias/<id>/editar | Renombrar | RF-11 |
| categorias | POST | /categorias/<id>/estado | Activar/desactivar | RF-11 |
| presupuesto | GET, POST | /presupuesto | Ver y guardar por mes | RF-12, RF-13 |
| presupuesto | POST | /presupuesto/copiar | Copiar del mes anterior | RF-12 |
| dashboard | GET | / | Dashboard del mes | RF-13 a RF-18 |
| dashboard | GET | /api/dashboard | JSON para Chart.js (`?mes=AAAA-MM&semana=AAAA-MM-DD`) | RF-15, RF-16 |
| reportes | GET | /reportes | Selector de período y agrupación | RF-19 |
| reportes | GET | /reportes/generar | Reporte en pantalla | RF-19 |
| reportes | GET | /reportes/pdf | Descarga del PDF | RF-20 |
| (raíz) | GET | /salud | `{"estado":"ok"}` sin datos, para monitoreo de disponibilidad (RNF-13) | RNF-13 |

Todas las rutas (salvo `/login` y `/salud`) exigen sesión. Las de `admin` exigen rol administrador. Las de modificación son POST con token CSRF. Toda consulta de datos filtra por `usuario_id = current_user.id`; un id ajeno responde **404** (no 403).

## 5. Modelo de datos (aprobado en EDT 2.2)

Impleméntalo con modelos SQLAlchemy 2 y genera la **migración inicial con Alembic** (no `db.create_all()` fuera de las pruebas). Este SQL es la referencia exacta del diseño físico:

```sql
CREATE TABLE usuario (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    correo VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,                       -- Argon2id
    rol VARCHAR(20) NOT NULL DEFAULT 'microemprendedor'
        CHECK (rol IN ('microemprendedor', 'administrador')),
    nombre_negocio VARCHAR(120),
    rubro VARCHAR(60),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    intentos_fallidos SMALLINT NOT NULL DEFAULT 0,
    bloqueado_hasta TIMESTAMPTZ,
    ultimo_acceso TIMESTAMPTZ,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE categoria (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuario(id) ON DELETE CASCADE,  -- NULL = plantilla predeterminada
    nombre VARCHAR(60) NOT NULL,
    predeterminada BOOLEAN NOT NULL DEFAULT FALSE,                -- TRUE si se copió de la plantilla (no se renombra)
    color CHAR(7) NOT NULL DEFAULT '#8B7BFF',
    activa BOOLEAN NOT NULL DEFAULT TRUE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_categoria_usuario_nombre ON categoria (usuario_id, lower(nombre)) WHERE usuario_id IS NOT NULL;
CREATE UNIQUE INDEX uq_categoria_predeterminada ON categoria (lower(nombre)) WHERE usuario_id IS NULL;
CREATE TABLE metodo_pago (id SMALLINT PRIMARY KEY, nombre VARCHAR(30) NOT NULL UNIQUE);
CREATE TABLE gasto (
    id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    categoria_id INTEGER REFERENCES categoria(id),
    metodo_pago_id SMALLINT REFERENCES metodo_pago(id),
    fecha DATE NOT NULL,
    monto NUMERIC(10,2) NOT NULL CHECK (monto > 0),
    descripcion VARCHAR(255),
    es_completo BOOLEAN NOT NULL DEFAULT FALSE,
    eliminado BOOLEAN NOT NULL DEFAULT FALSE,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    actualizado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_gasto_usuario_fecha ON gasto (usuario_id, fecha) WHERE eliminado = FALSE;
CREATE INDEX ix_gasto_usuario_categoria ON gasto (usuario_id, categoria_id) WHERE eliminado = FALSE;
CREATE TABLE presupuesto (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    categoria_id INTEGER NOT NULL REFERENCES categoria(id),
    anio SMALLINT NOT NULL CHECK (anio BETWEEN 2026 AND 2100),
    mes SMALLINT NOT NULL CHECK (mes BETWEEN 1 AND 12),
    monto NUMERIC(10,2) NOT NULL CHECK (monto >= 0),
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_presupuesto UNIQUE (usuario_id, categoria_id, anio, mes)
);
CREATE TABLE auditoria (
    id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuario(id) ON DELETE SET NULL,
    accion VARCHAR(20) NOT NULL,          -- INICIO_SESION, CIERRE_SESION, LOGIN_FALLIDO, CREAR, MODIFICAR, ELIMINAR, ACTIVAR, DESACTIVAR, RESTABLECER
    entidad VARCHAR(30) NOT NULL,
    entidad_id BIGINT,
    detalle JSONB,                        -- valores anteriores y nuevos (nunca contraseñas)
    ip INET,
    creado_en TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_auditoria_usuario_fecha ON auditoria (usuario_id, creado_en);
```

**Datos iniciales en la migración:**
- `metodo_pago`: (1 Efectivo), (2 Yape), (3 Plin), (4 Transferencia bancaria), (5 Tarjeta).
- Plantilla de categorías (`usuario_id NULL`) con su color (paleta de la sección 11):
  Insumos y materia prima `#8B7BFF` · Mercadería `#FFD166` · Servicios (luz, agua, gas) `#7EF0C0` · Alquiler `#93C5FD` · Transporte `#F9A8D4` · Sueldos y pagos a terceros `#FDBA74` · Mantenimiento `#BEF264` · Empaques y envases `#67E8F9` · Otros `#CBD5E1`.

**Notas del modelo:**
- `Gasto.evaluar_completitud()` y `Gasto.campos_faltantes()` encapsulan RN-01. `es_completo` se recalcula SIEMPRE al crear o modificar (decisión D-04).
- `Presupuesto.estado(ejecutado)` encapsula RN-05 y RN-06 → `Controlada` | `En alerta` | `Excedida`.
- La validación de fecha no futura (RN-04) va en el formulario y en `GastoService` (no como CHECK).
- `actualizado_en` se actualiza en cada modificación.
- **Cambio de diseño registrado (retroalimentación):** en EDT 2.2 todas las categorías tenían el color `#2A78D6`; ahora cada categoría tiene color propio por el nuevo diseño de interfaz. Regístralo en `docs/cambios/CR-01_diseno_interfaz.md` (ver sección 11.9).
