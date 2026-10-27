"""CU-01 a CU-03: inicio de sesión, cierre y cambio de contraseña (CP-01 a CP-07)."""
import time
from datetime import timedelta

import pytest
from itsdangerous.timed import TimestampSigner
from sqlalchemy import select

from app.models import Auditoria
from app.services.formato import ahora_lima

MENSAJE_GENERICO = "Correo o contraseña incorrectos."


def _eventos(sesion, accion):
    return list(sesion.scalars(select(Auditoria).where(Auditoria.accion == accion)))


# --- CP-01 Inicio de sesión válido (RF-01) ------------------------------------

def test_cp01_microemprendedor_ingresa_al_dashboard(cliente, crear_usuario, iniciar_sesion, sesion):
    usuario = crear_usuario()
    respuesta = iniciar_sesion("prueba.ana@ejemplo.com")
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/"

    inicio = cliente.get("/")
    assert inicio.status_code == 200
    assert "Inicio" in inicio.get_data(as_text=True)
    assert usuario.ultimo_acceso is not None

    eventos = _eventos(sesion, "INICIO_SESION")
    assert len(eventos) == 1
    assert eventos[0].usuario_id == usuario.id
    assert str(eventos[0].ip) == "127.0.0.1"


def test_cp01_administrador_ingresa_al_panel_de_usuarios(cliente, crear_admin, iniciar_sesion):
    crear_admin()
    respuesta = iniciar_sesion("prueba.admin@ejemplo.com")
    assert respuesta.headers["Location"] == "/admin/usuarios"
    # El administrador no tiene dashboard de gastos (RN-13)
    assert cliente.get("/").headers["Location"] == "/admin/usuarios"


def test_cp01_correo_sin_distinguir_mayusculas_ni_espacios(crear_usuario, iniciar_sesion):
    crear_usuario()
    respuesta = iniciar_sesion("  PRUEBA.Ana@Ejemplo.com ")
    assert respuesta.status_code == 302


def test_cp01_respeta_next_interno_e_ignora_externo(cliente, crear_usuario, iniciar_sesion):
    crear_usuario()
    respuesta = cliente.get("/cuenta/contrasena")
    assert respuesta.status_code == 302
    assert "/login?next=" in respuesta.headers["Location"]

    interna = cliente.post(
        "/login?next=/cuenta/contrasena", data={"correo": "prueba.ana@ejemplo.com", "contrasena": "clave1234"}
    )
    assert interna.headers["Location"] == "/cuenta/contrasena"


@pytest.mark.parametrize("destino", ["https://malicioso.com", "//malicioso.com", "/\\malicioso.com"])
def test_cp01_no_redirige_a_sitios_externos(cliente, crear_usuario, destino):
    crear_usuario()
    respuesta = cliente.post(
        f"/login?next={destino}", data={"correo": "prueba.ana@ejemplo.com", "contrasena": "clave1234"}
    )
    assert respuesta.headers["Location"] == "/"


def test_cp01_regenera_la_sesion_al_ingresar(cliente, crear_usuario, iniciar_sesion):
    crear_usuario()
    with cliente.session_transaction() as sesion_flask:
        sesion_flask["dato_previo"] = "fijado-por-un-atacante"
    iniciar_sesion("prueba.ana@ejemplo.com")
    with cliente.session_transaction() as sesion_flask:
        assert "dato_previo" not in sesion_flask
        assert sesion_flask.permanent is True


# --- CP-02 Credenciales inválidas ------------------------------------------------

@pytest.mark.parametrize(
    ("correo", "contrasena"),
    [("prueba.ana@ejemplo.com", "incorrecta1"), ("no.existe@ejemplo.com", "clave1234")],
)
def test_cp02_mensaje_generico(cliente, crear_usuario, iniciar_sesion, sesion, correo, contrasena):
    crear_usuario()
    respuesta = iniciar_sesion(correo, contrasena)
    assert respuesta.status_code == 200
    assert MENSAJE_GENERICO in respuesta.get_data(as_text=True)
    assert cliente.get("/").status_code == 302
    assert len(_eventos(sesion, "LOGIN_FALLIDO")) == 1


def test_cp02_campos_vacios(iniciar_sesion):
    respuesta = iniciar_sesion("", "")
    texto = respuesta.get_data(as_text=True)
    assert "Escribe tu correo." in texto
    assert "Escribe tu contraseña." in texto


# --- CP-03 Bloqueo tras 5 intentos (RNF-11, CU-01 4b) ----------------------------

def test_cp03_bloqueo_de_15_minutos_tras_5_intentos(crear_usuario, iniciar_sesion, sesion):
    usuario = crear_usuario()
    for _ in range(4):
        assert MENSAJE_GENERICO in iniciar_sesion("prueba.ana@ejemplo.com", "mala1234").get_data(as_text=True)

    quinto = iniciar_sesion("prueba.ana@ejemplo.com", "mala1234").get_data(as_text=True)
    assert "Por seguridad, tu cuenta está bloqueada. Inténtalo de nuevo en 15 minutos." in quinto
    assert usuario.bloqueado_hasta is not None

    # Durante el bloqueo, ni la contraseña correcta permite ingresar
    correcta = iniciar_sesion("prueba.ana@ejemplo.com")
    assert correcta.status_code == 200
    assert "tu cuenta está bloqueada" in correcta.get_data(as_text=True)


def test_cp03_al_vencer_el_bloqueo_puede_ingresar(crear_usuario, iniciar_sesion, sesion):
    usuario = crear_usuario()
    usuario.bloqueado_hasta = ahora_lima() - timedelta(seconds=1)
    sesion.commit()
    assert iniciar_sesion("prueba.ana@ejemplo.com").status_code == 302
    assert usuario.bloqueado_hasta is None
    assert usuario.intentos_fallidos == 0


def test_cp03_un_acceso_correcto_reinicia_el_contador(crear_usuario, iniciar_sesion, cliente):
    usuario = crear_usuario()
    for _ in range(4):
        iniciar_sesion("prueba.ana@ejemplo.com", "mala1234")
    iniciar_sesion("prueba.ana@ejemplo.com")
    assert usuario.intentos_fallidos == 0


# --- CP-04 Cuenta desactivada (CU-01 4c) ------------------------------------------

def test_cp04_cuenta_desactivada_no_ingresa(cliente, crear_usuario, iniciar_sesion):
    crear_usuario(activo=False)
    respuesta = iniciar_sesion("prueba.ana@ejemplo.com")
    assert respuesta.status_code == 200
    assert "Tu cuenta está desactivada. Comunícate con el administrador." in respuesta.get_data(as_text=True)
    assert cliente.get("/").status_code == 302


def test_cp04_desactivar_cierra_la_sesion_abierta(cliente, crear_usuario, iniciar_sesion, sesion):
    usuario = crear_usuario()
    iniciar_sesion("prueba.ana@ejemplo.com")
    assert cliente.get("/").status_code == 200
    usuario.activo = False
    sesion.commit()
    assert cliente.get("/").status_code == 302


# --- CP-05 Cerrar sesión (RF-02) -----------------------------------------------

def test_cp05_cerrar_sesion(cliente, crear_usuario, iniciar_sesion, sesion):
    crear_usuario()
    iniciar_sesion("prueba.ana@ejemplo.com")
    respuesta = cliente.post("/logout", follow_redirects=True)
    assert "Sesión cerrada." in respuesta.get_data(as_text=True)
    assert len(_eventos(sesion, "CIERRE_SESION")) == 1

    for ruta in ("/", "/cuenta/contrasena", "/admin/usuarios"):
        protegida = cliente.get(ruta)
        assert protegida.status_code == 302
        assert protegida.headers["Location"].startswith("/login")


def test_cp05_cerrar_sesion_solo_por_post(cliente, crear_usuario, iniciar_sesion):
    crear_usuario()
    iniciar_sesion("prueba.ana@ejemplo.com")
    assert cliente.get("/logout").status_code == 405
    assert cliente.get("/").status_code == 200


# --- CP-06 Cierre automático tras 30 minutos sin actividad (RF-02) -------------

def test_cp06_sesion_expira_tras_30_minutos(cliente, crear_usuario, iniciar_sesion, monkeypatch):
    crear_usuario()
    iniciar_sesion("prueba.ana@ejemplo.com")
    ahora = int(time.time())

    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: ahora + 29 * 60)
    assert cliente.get("/").status_code == 200  # actividad: la sesión se renueva

    monkeypatch.setattr(TimestampSigner, "get_timestamp", lambda self: ahora + 29 * 60 + 31 * 60)
    respuesta = cliente.get("/")
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/login")


# --- CP-07 Cambiar contraseña (RF-03) ---------------------------------------------

def _cambiar(cliente, actual, nueva, confirmacion=None):
    return cliente.post(
        "/cuenta/contrasena",
        data={
            "contrasena_actual": actual,
            "contrasena_nueva": nueva,
            "confirmacion": nueva if confirmacion is None else confirmacion,
        },
    )


@pytest.mark.parametrize(
    ("actual", "nueva", "confirmacion", "mensaje"),
    [
        ("otra1234", "nueva1234", None, "La contraseña actual no es correcta."),
        ("clave1234", "nueva1234", "nueva9999", "Las contraseñas nuevas no coinciden."),
        ("clave1234", "corta1", None, "al menos 8 caracteres e incluir letras y números"),
        ("clave1234", "soloLetras", None, "al menos 8 caracteres e incluir letras y números"),
        ("clave1234", "12345678", None, "al menos 8 caracteres e incluir letras y números"),
        ("clave1234", "clave1234", None, "debe ser distinta de la actual"),
    ],
)
def test_cp07_validaciones(cliente, crear_usuario, iniciar_sesion, actual, nueva, confirmacion, mensaje):
    usuario = crear_usuario()
    iniciar_sesion("prueba.ana@ejemplo.com")
    respuesta = _cambiar(cliente, actual, nueva, confirmacion)
    assert respuesta.status_code == 200
    assert mensaje in respuesta.get_data(as_text=True)
    assert usuario.verificar_contrasena("clave1234")


def test_cp07_la_anterior_deja_de_funcionar(cliente, crear_usuario, iniciar_sesion, sesion):
    crear_usuario()
    iniciar_sesion("prueba.ana@ejemplo.com")
    respuesta = _cambiar(cliente, "clave1234", "nueva5678")
    assert respuesta.status_code == 302
    assert "se cambió correctamente" in cliente.get("/cuenta/contrasena").get_data(as_text=True)

    cliente.post("/logout")
    assert MENSAJE_GENERICO in iniciar_sesion("prueba.ana@ejemplo.com", "clave1234").get_data(as_text=True)
    assert iniciar_sesion("prueba.ana@ejemplo.com", "nueva5678").status_code == 302

    cambio = [e for e in _eventos(sesion, "MODIFICAR") if e.entidad == "usuario"]
    assert len(cambio) == 1
    assert "nueva5678" not in str(cambio[0].detalle)


def test_cp07_politica_visible(cliente, crear_usuario, iniciar_sesion):
    crear_usuario()
    iniciar_sesion("prueba.ana@ejemplo.com")
    texto = cliente.get("/cuenta/contrasena").get_data(as_text=True)
    assert "al menos 8 caracteres e incluir letras y números" in texto
    assert "prueba.ana@ejemplo.com" in texto
