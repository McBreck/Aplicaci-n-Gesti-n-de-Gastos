"""CU-04 Gestionar usuarios (CP-08, CP-09) y control de acceso a las rutas de administración (CP-29)."""
import re

import pytest
from sqlalchemy import select

from app.models import Auditoria, Categoria, Usuario

DATOS_NUEVO = {
    "nombre": "PRUEBA Rosa Díaz",
    "correo": "Prueba.Rosa@Ejemplo.com",
    "nombre_negocio": "PRUEBA Panadería Rosa",
    "rubro": "Panadería",
    "contrasena_temporal": "temporal123",
}


@pytest.fixture
def admin_con_sesion(crear_admin, iniciar_sesion):
    admin = crear_admin()
    iniciar_sesion("prueba.admin@ejemplo.com")
    return admin


def _crear_cuenta(cliente, **cambios):
    return cliente.post("/admin/usuarios/nuevo", data={**DATOS_NUEVO, **cambios})


def _cuenta(sesion, correo="prueba.rosa@ejemplo.com"):
    return sesion.scalar(select(Usuario).where(Usuario.correo == correo))


# --- CP-08 Alta de cuenta -----------------------------------------------------------

def test_cp08_crea_cuenta_y_copia_las_categorias(cliente, admin_con_sesion, sesion):
    respuesta = _crear_cuenta(cliente)
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/admin/usuarios"

    cuenta = _cuenta(sesion)
    assert cuenta.rol == "microemprendedor"
    assert cuenta.nombre_negocio == "PRUEBA Panadería Rosa"
    assert cuenta.password_hash.startswith("$argon2id$")

    copiadas = list(sesion.scalars(select(Categoria).where(Categoria.usuario_id == cuenta.id).order_by(Categoria.id)))
    plantilla = list(sesion.scalars(select(Categoria).where(Categoria.usuario_id.is_(None)).order_by(Categoria.id)))
    assert len(copiadas) == 9
    assert [(c.nombre, c.color) for c in copiadas] == [(c.nombre, c.color) for c in plantilla]
    assert all(c.predeterminada and c.activa for c in copiadas)

    evento = sesion.scalar(select(Auditoria).where(Auditoria.accion == "CREAR", Auditoria.entidad_id == cuenta.id))
    assert evento.usuario_id == admin_con_sesion.id
    assert "temporal123" not in str(evento.detalle)


def test_cp08_cuenta_nueva_ingresa_con_la_contrasena_temporal(cliente, admin_con_sesion, iniciar_sesion):
    _crear_cuenta(cliente)
    cliente.post("/logout")
    respuesta = iniciar_sesion("prueba.rosa@ejemplo.com", "temporal123")
    assert respuesta.headers["Location"] == "/"


def test_cp08_listado_muestra_la_cuenta(cliente, admin_con_sesion):
    _crear_cuenta(cliente)
    texto = cliente.get("/admin/usuarios").get_data(as_text=True)
    assert "PRUEBA Rosa Díaz" in texto
    assert "PRUEBA Panadería Rosa" in texto
    assert "Activa" in texto
    assert "Nunca" in texto


@pytest.mark.parametrize(
    ("cambios", "mensaje"),
    [
        ({"nombre": ""}, "Escribe el nombre de la persona."),
        ({"correo": "sin-arroba"}, "Escribe un correo válido"),
        ({"contrasena_temporal": "corta"}, "al menos 8 caracteres e incluir letras y números"),
    ],
)
def test_cp08_validaciones(cliente, admin_con_sesion, sesion, cambios, mensaje):
    respuesta = _crear_cuenta(cliente, **cambios)
    assert respuesta.status_code == 200
    assert mensaje in respuesta.get_data(as_text=True)
    assert _cuenta(sesion) is None


# --- CP-09 Correo duplicado, edición, activación y restablecimiento ---------------

def test_cp09_correo_duplicado_es_conflicto(cliente, admin_con_sesion, sesion):
    _crear_cuenta(cliente)
    respuesta = _crear_cuenta(cliente, correo="PRUEBA.ROSA@ejemplo.com")
    assert respuesta.status_code == 409
    assert "Ya existe una cuenta con ese correo." in respuesta.get_data(as_text=True)


def test_cp09_editar_cuenta(cliente, admin_con_sesion, sesion):
    _crear_cuenta(cliente)
    cuenta = _cuenta(sesion)
    formulario = cliente.get(f"/admin/usuarios/{cuenta.id}/editar").get_data(as_text=True)
    assert "PRUEBA Panadería Rosa" in formulario

    respuesta = cliente.post(
        f"/admin/usuarios/{cuenta.id}/editar",
        data={"nombre": "PRUEBA Rosa Díaz Vega", "correo": "prueba.rosa@ejemplo.com",
              "nombre_negocio": "PRUEBA Panadería Rosa", "rubro": "Pastelería"},
    )
    assert respuesta.status_code == 302
    assert cuenta.nombre == "PRUEBA Rosa Díaz Vega"
    assert cuenta.rubro == "Pastelería"

    evento = sesion.scalar(select(Auditoria).where(Auditoria.accion == "MODIFICAR", Auditoria.entidad_id == cuenta.id))
    assert evento.detalle == {
        "anterior": {"nombre": "PRUEBA Rosa Díaz", "rubro": "Panadería"},
        "nuevo": {"nombre": "PRUEBA Rosa Díaz Vega", "rubro": "Pastelería"},
    }


def test_cp09_editar_con_correo_de_otra_cuenta_es_conflicto(cliente, admin_con_sesion, sesion):
    _crear_cuenta(cliente)
    _crear_cuenta(cliente, correo="prueba.luis@ejemplo.com", nombre="PRUEBA Luis")
    luis = _cuenta(sesion, "prueba.luis@ejemplo.com")
    respuesta = cliente.post(
        f"/admin/usuarios/{luis.id}/editar",
        data={"nombre": "PRUEBA Luis", "correo": "prueba.rosa@ejemplo.com"},
    )
    assert respuesta.status_code == 409
    assert luis.correo == "prueba.luis@ejemplo.com"


def test_cp09_desactivar_y_activar(cliente, admin_con_sesion, sesion, iniciar_sesion):
    _crear_cuenta(cliente)
    cuenta = _cuenta(sesion)
    cliente.post(f"/admin/usuarios/{cuenta.id}/estado")
    assert cuenta.activo is False
    assert "Inactiva" in cliente.get("/admin/usuarios").get_data(as_text=True)

    cliente.post("/logout")
    rechazo = iniciar_sesion("prueba.rosa@ejemplo.com", "temporal123")
    assert "Tu cuenta está desactivada" in rechazo.get_data(as_text=True)

    iniciar_sesion("prueba.admin@ejemplo.com")
    cliente.post(f"/admin/usuarios/{cuenta.id}/estado")
    assert cuenta.activo is True
    acciones = [e.accion for e in sesion.scalars(select(Auditoria).where(Auditoria.entidad_id == cuenta.id))]
    assert "DESACTIVAR" in acciones and "ACTIVAR" in acciones


def test_cp09_restablecer_contrasena(cliente, admin_con_sesion, sesion, iniciar_sesion):
    _crear_cuenta(cliente)
    cuenta = _cuenta(sesion)
    cuenta.intentos_fallidos = 3
    sesion.commit()

    respuesta = cliente.post(f"/admin/usuarios/{cuenta.id}/restablecer")
    assert respuesta.status_code == 200
    texto = respuesta.get_data(as_text=True)
    temporal = re.search(r'id="contrasenaTemporal"[^>]*>([^<]+)<', texto).group(1)
    assert len(temporal) == 10
    assert "no se volverá a mostrar" in texto
    assert cuenta.intentos_fallidos == 0

    # Se muestra una sola vez: no queda en el listado ni en la auditoría
    assert temporal not in cliente.get("/admin/usuarios").get_data(as_text=True)
    evento = sesion.scalar(select(Auditoria).where(Auditoria.accion == "RESTABLECER"))
    assert evento.detalle is None

    cliente.post("/logout")
    assert iniciar_sesion("prueba.rosa@ejemplo.com", "temporal123").status_code == 200
    assert iniciar_sesion("prueba.rosa@ejemplo.com", temporal).status_code == 302


def test_cp09_cuenta_inexistente_responde_404(cliente, admin_con_sesion):
    assert cliente.get("/admin/usuarios/999999/editar").status_code == 404
    assert cliente.post("/admin/usuarios/999999/estado").status_code == 404


def test_cp09_cuentas_de_administrador_no_se_gestionan_desde_el_panel(cliente, admin_con_sesion, crear_admin):
    otro = crear_admin("prueba.admin2@ejemplo.com")
    assert cliente.get(f"/admin/usuarios/{otro.id}/editar").status_code == 404
    assert cliente.post(f"/admin/usuarios/{otro.id}/estado").status_code == 404
    assert cliente.post(f"/admin/usuarios/{admin_con_sesion.id}/estado").status_code == 404
    assert "prueba.admin2@ejemplo.com" not in cliente.get("/admin/usuarios").get_data(as_text=True)


# --- CP-29 Rutas de administración ------------------------------------------------

RUTAS_ADMIN = [
    ("get", "/admin/usuarios"),
    ("get", "/admin/usuarios/nuevo"),
    ("post", "/admin/usuarios/nuevo"),
    ("get", "/admin/usuarios/1/editar"),
    ("post", "/admin/usuarios/1/estado"),
    ("post", "/admin/usuarios/1/restablecer"),
]


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS_ADMIN)
def test_cp29_microemprendedor_recibe_403_en_rutas_admin(cliente, crear_usuario, iniciar_sesion, metodo, ruta):
    crear_usuario()
    iniciar_sesion("prueba.ana@ejemplo.com")
    respuesta = getattr(cliente, metodo)(ruta)
    assert respuesta.status_code == 403
    assert "No tienes acceso" in respuesta.get_data(as_text=True)


@pytest.mark.parametrize(("metodo", "ruta"), RUTAS_ADMIN)
def test_cp29_sin_sesion_redirige_al_login(cliente, sesion, metodo, ruta):
    respuesta = getattr(cliente, metodo)(ruta)
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"].startswith("/login")
