"""Seguridad básica (sección 10): CSRF (CP-30), contraseñas y bitácora (CP-31), límites y errores."""
import re

import pytest
from sqlalchemy import select

from app import create_app
from app.extensions import limiter
from app.models import Auditoria


def _token_csrf(html: str) -> str:
    return re.search(r'name="csrf_token" type="hidden" value="([^"]+)"', html).group(1)


@pytest.fixture
def csrf_activo(app, monkeypatch):
    monkeypatch.setitem(app.config, "WTF_CSRF_ENABLED", True)


# --- CP-30 Protección CSRF (RNF-10, A08) ---------------------------------------------

def test_cp30_login_sin_token_csrf_es_rechazado(cliente, crear_usuario, csrf_activo):
    crear_usuario()
    respuesta = cliente.post("/login", data={"correo": "prueba.ana@ejemplo.com", "contrasena": "clave1234"})
    assert respuesta.status_code == 400
    assert "El formulario expiró por seguridad" in respuesta.get_data(as_text=True)


def test_cp30_login_con_token_csrf_funciona(cliente, crear_usuario, csrf_activo):
    crear_usuario()
    token = _token_csrf(cliente.get("/login").get_data(as_text=True))
    respuesta = cliente.post(
        "/login", data={"correo": "prueba.ana@ejemplo.com", "contrasena": "clave1234", "csrf_token": token}
    )
    assert respuesta.status_code == 302


def test_cp30_acciones_post_sin_token_son_rechazadas(cliente, crear_admin, crear_usuario, iniciar_sesion, app, monkeypatch):
    crear_admin()
    cuenta = crear_usuario()
    iniciar_sesion("prueba.admin@ejemplo.com")
    monkeypatch.setitem(app.config, "WTF_CSRF_ENABLED", True)
    assert cliente.post(f"/admin/usuarios/{cuenta.id}/estado").status_code == 400
    assert cliente.post("/logout").status_code == 400
    assert cuenta.activo is True


# --- CP-31 Contraseñas protegidas (RNF-07, A02, A09) ------------------------------------

def test_cp31_contrasenas_solo_como_hash_y_nunca_en_la_bitacora(cliente, crear_admin, iniciar_sesion, sesion):
    admin = crear_admin()
    iniciar_sesion("prueba.admin@ejemplo.com", "contrasena-equivocada9")
    iniciar_sesion("prueba.admin@ejemplo.com")
    cliente.post(
        "/admin/usuarios/nuevo",
        data={"nombre": "PRUEBA Rosa", "correo": "prueba.rosa@ejemplo.com", "contrasena_temporal": "secreta123"},
    )
    cliente.post(
        "/cuenta/contrasena",
        data={"contrasena_actual": "clave1234", "contrasena_nueva": "otraClave99", "confirmacion": "otraClave99"},
    )

    assert admin.password_hash.startswith("$argon2id$")
    bitacora = " ".join(str(evento.detalle) for evento in sesion.scalars(select(Auditoria)))
    for secreto in ("clave1234", "contrasena-equivocada9", "secreta123", "otraClave99"):
        assert secreto not in bitacora


def test_cp31_rehash_si_cambian_los_parametros_de_argon2(crear_usuario, iniciar_sesion):
    from argon2 import PasswordHasher

    usuario = crear_usuario()
    usuario.password_hash = PasswordHasher(time_cost=1, memory_cost=8192).hash("clave1234")
    anterior = usuario.password_hash
    assert usuario.necesita_rehash()
    iniciar_sesion("prueba.ana@ejemplo.com")
    assert usuario.password_hash != anterior
    assert not usuario.necesita_rehash()


def test_auditoria_descarta_claves_sensibles(app, sesion):
    from app.services import auditoria

    evento = auditoria.registrar(
        "MODIFICAR", "usuario", detalle={"nombre": "Ana", "contrasena": "x", "nuevo": {"password_hash": "y"}}
    )
    assert evento.detalle == {"nombre": "Ana", "nuevo": {}}


# --- Límite de intentos por IP en /login (A04) -----------------------------------------

def test_limite_de_10_intentos_por_minuto_en_login(sesion, monkeypatch):
    # El limitador solo se configura si está activo al crear la app: se usa una app aparte
    monkeypatch.setattr(limiter, "enabled", limiter.enabled)
    cliente = create_app("pruebas", RATELIMIT_ENABLED=True).test_client()
    limiter.reset()
    try:
        for _ in range(10):
            assert cliente.post("/login", data={"correo": "x@ejemplo.com", "contrasena": "x"}).status_code == 200
        bloqueada = cliente.post("/login", data={"correo": "x@ejemplo.com", "contrasena": "x"})
        assert bloqueada.status_code == 429
        assert "Demasiados intentos" in bloqueada.get_data(as_text=True)
        # Ver la página de inicio de sesión sigue permitido
        assert cliente.get("/login").status_code == 200
    finally:
        limiter.reset()


# --- Sesión, cookies y errores (A05, A07) ------------------------------------------------

def test_cookie_de_sesion_httponly_y_samesite(cliente, crear_usuario, iniciar_sesion):
    crear_usuario()
    respuesta = iniciar_sesion("prueba.ana@ejemplo.com")
    cookie = respuesta.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_pagina_404_con_diseno_y_sin_trazas(cliente, crear_usuario, iniciar_sesion):
    crear_usuario()
    iniciar_sesion("prueba.ana@ejemplo.com")
    respuesta = cliente.get("/no-existe")
    texto = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 404
    assert "Página no encontrada" in texto
    assert "Traceback" not in texto
    assert "cg-logo" in texto


def test_pagina_404_sin_sesion(cliente, sesion):
    respuesta = cliente.get("/no-existe")
    assert respuesta.status_code == 404
    assert "Volver al inicio" in respuesta.get_data(as_text=True)


def test_obtener_propio_o_404(app, cliente, crear_usuario, iniciar_sesion, sesion):
    from werkzeug.exceptions import NotFound

    from app.models import Categoria
    from app.seguridad import obtener_propio_o_404

    ana = crear_usuario("prueba.ana@ejemplo.com")
    luis = crear_usuario("prueba.luis@ejemplo.com")
    propia = Categoria(usuario_id=ana.id, nombre="Delivery")
    ajena = Categoria(usuario_id=luis.id, nombre="Delivery")
    sesion.add_all([propia, ajena])
    sesion.commit()

    with app.test_request_context():
        from flask_login import login_user

        login_user(ana)
        assert obtener_propio_o_404(Categoria, propia.id) is propia
        with pytest.raises(NotFound):
            obtener_propio_o_404(Categoria, ajena.id)
        with pytest.raises(NotFound):
            obtener_propio_o_404(Categoria, 999999)
