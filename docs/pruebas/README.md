# Pruebas de ControlGastos (fase 4.0)

Material para ejecutar y documentar la fase 4.0 Pruebas (EDT 4.1–4.7). Cada caso de prueba (CP) tiene una lista de verificación con pasos y resultado esperado; casi todos tienen, además, pruebas automatizadas que se ejecutan con `pytest`.

| Documento | Contenido |
|---|---|
| [4.2_pruebas_funcionales.md](4.2_pruebas_funcionales.md) | CP-01 a CP-27: acceso, cuentas, gastos, categorías, presupuesto, dashboard y reportes |
| [4.4_rendimiento.md](4.4_rendimiento.md) | CP-28: reporte de un mes con 500 gastos, cronometrado 10 veces |
| [4.5_seguridad.md](4.5_seguridad.md) | CP-29 a CP-32 y revisión OWASP Top 10 2021 |
| [4.6_responsivo_y_sus.md](4.6_responsivo_y_sus.md) | CP-33 (celular, tableta y escritorio) y CP-34 (cuestionario SUS, fuera de la app) |
| [plantilla_defectos.md](plantilla_defectos.md) | Registro de defectos DEF-nn |

> Estas pruebas verifican el **software**. Los indicadores de la investigación (ECG, TRG y CRG) y el SUS se miden fuera de la aplicación, con fichas, cronómetro y formularios propios. La aplicación no guarda esas mediciones.

## Antes de empezar

1. Instala el proyecto como indica el [README principal](../../README.md) y aplica las migraciones:
   ```powershell
   flask db upgrade
   ```
2. Crea la cuenta de administrador de prueba (nombre `PRUEBA Admin`, correo `prueba.admin@controlgastos.test`):
   ```powershell
   flask crear-admin
   ```
3. Crea la cuenta de demostración **PRUEBA Panadería** y, para CP-28, la cuenta **PRUEBA Rendimiento**:
   ```powershell
   flask demo crear
   flask demo rendimiento
   ```
4. Inicia el servidor y abre http://127.0.0.1:5000:
   ```powershell
   flask run --debug
   ```
   Para CP-28 usa `flask run` (sin `--debug`), como se explica en 4.4.
5. Ejecuta las pruebas automatizadas y guarda la salida como evidencia (ver abajo).
6. Al terminar, borra todos los datos de prueba:
   ```powershell
   flask demo borrar
   ```

## Pruebas automatizadas

```powershell
pytest -v                       # toda la suite, con el nombre de cada prueba
pytest -k cp10 -v               # solo las pruebas de un caso (aquí, CP-10)
pytest --cov=app/services       # cobertura de los servicios (RNF-15: 70 % o más)
python -m flake8                # estilo PEP 8 (RNF-15); sin mensajes = sin observaciones
```

Para guardar la salida como evidencia:
```powershell
pytest -v | Out-File evidencia_pytest_2026-11-03.txt -Encoding utf8
```
En bash: `pytest -v > evidencia_pytest_2026-11-03.txt`

- Las pruebas de cada caso se llaman `test_cpNN_...` (por ejemplo, `test_cp10_registrar_gasto_completo`).
- `tests/test_trazabilidad.py` falla si algún caso entre CP-01 y CP-32 se queda sin prueba automatizada.
- Las pruebas usan la base de `TEST_DATABASE_URL`, que se borra en cada ejecución; nunca tocan la base de desarrollo.
- La integración continua de GitHub (pestaña **Actions**) ejecuta flake8, las migraciones y toda la suite en cada `push`.

## Cómo registrar los resultados

- **Estados:** Pasa, Falla, Bloqueada (no se pudo ejecutar) o No aplica.
- **Si un caso falla:** registra un defecto con la [plantilla](plantilla_defectos.md) y anota su código (DEF-nn) en la lista del caso.
- **Evidencias:** capturas de pantalla o salidas de consola con fecha. Nombre sugerido: `CP-10_Pasa_2026-11-03.png`.
- **Datos:** usa siempre cuentas con el prefijo `PRUEBA`. Nunca presentes esos datos como resultados de la investigación.

## Catálogo de casos de prueba

| CP | Qué cubre | Requisitos | Tipo | Documento |
|---|---|---|---|---|
| CP-01 | Ingreso válido | RF-01 · CU-01 | Automatizada y manual | 4.2 |
| CP-02 | Datos incorrectos | RF-01 · CU-01 | Automatizada y manual | 4.2 |
| CP-03 | Bloqueo tras 5 intentos | RNF-11 · CU-01 (4b) | Automatizada y manual | 4.2 |
| CP-04 | Cuenta desactivada | RF-04 · CU-01 (4c) | Automatizada y manual | 4.2 |
| CP-05 | Cierre de sesión | RF-02 · CU-02 | Automatizada y manual | 4.2 |
| CP-06 | Cierre por inactividad | RF-02 · CU-02 | Automatizada y manual | 4.2 |
| CP-07 | Cambio de contraseña | RF-03 · CU-03 | Automatizada y manual | 4.2 |
| CP-08 | Alta de cuenta | RF-04 · CU-04 · RN-11 | Automatizada y manual | 4.2 |
| CP-09 | Duplicado, edición, estado y restablecimiento | RF-04 · CU-04 | Automatizada y manual | 4.2 |
| CP-10 | Registro completo | RF-05, RF-06 · CU-05, CU-15 | Automatizada y manual | 4.2 |
| CP-11 | Registro solo con fecha y monto | RF-05, RF-06 · RN-02 · CU-05 (7a) | Automatizada y manual | 4.2 |
| CP-12 | Monto inválido | RF-05 · RN-03 | Automatizada y manual | 4.2 |
| CP-13 | Fecha futura | RN-04 | Automatizada y manual | 4.2 |
| CP-14 | Completar al editar | RF-07 · CU-06 | Automatizada y manual | 4.2 |
| CP-15 | Eliminar | RF-08 · RN-09 · CU-07 | Automatizada y manual | 4.2 |
| CP-16 | Filtros y paginación | RF-09 · CU-08 (4a) | Automatizada y manual | 4.2 |
| CP-17 | Completitud y dato más omitido | RF-10 · RN-01 · CU-15 | Automatizada y manual | 4.2 |
| CP-18 | Crear y renombrar categorías | RF-11 · CU-09 | Automatizada y manual | 4.2 |
| CP-19 | Desactivar categoría | RF-11 · CU-09 | Automatizada y manual | 4.2 |
| CP-20 | Presupuesto y copia del mes anterior | RF-12 · RN-10 · CU-10 (3a) | Automatizada y manual | 4.2 |
| CP-21 | Comparación y alertas (79.9, 80, 100 y 100.1 %) | RF-13, RF-14 · RN-05, RN-06 | Automatizada y manual | 4.2 |
| CP-22 | Los cuatro KPI del dashboard coinciden con el listado | RF-15 · CU-11 | Automatizada y manual | 4.2 |
| CP-23 | Datos de los gráficos (`/api/dashboard`) | RF-15, RF-16 · RNF-09 | Automatizada y manual | 4.2 |
| CP-24 | Proyección y recomendaciones | RF-17, RF-18 · RN-07, RN-08 · CU-12 (1a, 3a) | Automatizada y manual | 4.2 |
| CP-25 | Estados especiales, tarjetas rápidas y actividad | RF-15 · RNF-05 · CU-11 (2a) | Automatizada y manual | 4.2 |
| CP-26 | Reporte en pantalla | RF-19 · CU-13 (4a) | Automatizada y manual | 4.2 |
| CP-27 | Exportar a PDF | RF-20 · CU-14 (2a) | Automatizada y manual | 4.2 |
| CP-28 | Reporte de un mes con 500 gastos en menos de 1 s | RNF-01 | Manual con cronómetro (más una automatizada orientativa) | 4.4 |
| CP-29 | Control de acceso (403 y 404) | RNF-09 · RN-13 | Automatizada y manual | 4.5 |
| CP-30 | Protección CSRF | RNF-10 | Automatizada y manual | 4.5 |
| CP-31 | Contraseñas protegidas | RNF-07 | Automatizada y manual | 4.5 |
| CP-32 | HTTPS con redirección 301 | RNF-08 | Automatizada (aplicación) y manual en el servidor (EDT 5.3) | 4.5 |
| CP-33 | Diseño responsivo sin desplazamiento horizontal | RNF-04, RNF-16 | Manual | 4.6 |
| CP-34 | Usabilidad con el cuestionario SUS (meta ≥ 68) | Usabilidad (sección 1) | Manual, fuera de la app | 4.6 |
