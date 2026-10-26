# 05 — Seguridad

> Fuente: prompt maestro de implementación, sección 10.

## 10. Seguridad (OWASP Top 10 2021, nivel básico)

- **A01 Control de acceso:** `@login_required` en todo; decorador `rol_requerido("administrador")`; helper `obtener_propio_o_404(Modelo, id)`; el admin no tiene rutas de gastos.
- **A02 Criptografía:** Argon2id (`argon2-cffi`, `PasswordHasher()` por defecto) con rehash si cambian parámetros; HTTPS en producción; `SECRET_KEY` larga desde `.env`.
- **A03 Inyección:** solo ORM / `select()` con parámetros; autoescape de Jinja2 activo; nunca `|safe` con datos del usuario; datos para JS con `|tojson`.
- **A04 Diseño inseguro:** bloqueo 5 intentos/15 min en BD (`intentos_fallidos`, `bloqueado_hasta`); Flask-Limiter en `/login` (10 por minuto por IP).
- **A05 Configuración:** `DEBUG=False` en producción; Flask-Talisman con CSP `default-src 'self'` (sin scripts en línea: todo JS en archivos `.js`; datos iniciales en atributos `data-*` o `<script type="application/json">`), `force_https` solo en producción, HSTS; cabeceras de Nginx; `ProxyFix(x_for=1, x_proto=1)` en producción.
- **A07 Autenticación:** sesión de 30 min con renovación en cada petición (`PERMANENT_SESSION_LIFETIME`, `SESSION_REFRESH_EACH_REQUEST`), cookies `HttpOnly`, `SameSite=Lax`, `Secure` en producción; sin "recordarme"; `session_protection="strong"`; regenerar sesión al iniciar.
- **A08 Integridad:** CSRF de Flask-WTF global (`CSRFProtect`), también en `fetch` POST si existiera (cabecera `X-CSRFToken`).
- **A09 Registro:** AuditoriaService con IP (`request.remote_addr` tras ProxyFix); nunca registrar contraseñas; incluir `LOGIN_FALLIDO`.
- **Errores:** páginas 400, 403, 404, 429 y 500 con el diseño de la app y mensajes amables, sin trazas.
