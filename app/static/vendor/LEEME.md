# Archivos de interfaz de terceros

Se sirven desde la propia aplicación (sin CDN) para que la política CSP sea `default-src 'self'`. No se modifican; para actualizar una versión, se descarga en una carpeta nueva con el número de versión y se cambian las referencias en las plantillas.

| Carpeta | Versión | Licencia | Origen (descargado el 26/10/2026) |
|---|---|---|---|
| `bootstrap-5.3.3/` | 5.3.3 | MIT | `https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/` (`css/bootstrap.min.css`, `js/bootstrap.bundle.min.js`) |
| `bootstrap-icons-1.11.3/` | 1.11.3 | MIT | `https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/` (`bootstrap-icons.min.css`, `fonts/*.woff2`, `fonts/*.woff`) |
| `chartjs-4.4.9/` | 4.4.9 | MIT | `https://cdn.jsdelivr.net/npm/chart.js@4.4.9/dist/chart.umd.js` |
| `inter-5.2.8/` | 5.2.8 (@fontsource/inter) | SIL OFL 1.1 | `https://cdn.jsdelivr.net/npm/@fontsource/inter@5.2.8/files/` (latín, pesos 400, 500 y 600); `inter.css` es propio |

Verificación de integridad (hash SRI oficial de Bootstrap 5.3.3):

- `bootstrap.min.css` → `sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH`
- `bootstrap.bundle.min.js` → `sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz`
