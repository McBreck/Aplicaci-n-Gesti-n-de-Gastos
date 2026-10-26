"""UsuarioService: creación y mantenimiento de cuentas (RF-04).

En la EDT 3.1 solo incluye lo necesario para `flask crear-admin`; la gestión
completa de cuentas se agrega en la EDT 3.2.
"""
import re

from sqlalchemy import func, select

from app.extensions import db
from app.models import Usuario
from app.models.usuario import ROL_ADMINISTRADOR

LONGITUD_MINIMA_CONTRASENA = 8
MENSAJE_POLITICA_CONTRASENA = (
    "La contraseña debe tener al menos 8 caracteres e incluir letras y números."
)
_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ErrorUsuario(Exception):
    """Error de negocio con un mensaje listo para mostrar al usuario."""


def validar_contrasena(contrasena: str) -> None:
    """Política de RF-03: mínimo 8 caracteres, con letras y números."""
    tiene_letra = any(caracter.isalpha() for caracter in contrasena)
    tiene_numero = any(caracter.isdigit() for caracter in contrasena)
    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA or not (tiene_letra and tiene_numero):
        raise ErrorUsuario(MENSAJE_POLITICA_CONTRASENA)


def normalizar_correo(correo: str) -> str:
    return (correo or "").strip().lower()


def existe_correo(correo: str) -> bool:
    consulta = select(Usuario.id).where(func.lower(Usuario.correo) == normalizar_correo(correo))
    return db.session.scalar(consulta) is not None


def crear_administrador(nombre: str, correo: str, contrasena: str) -> Usuario:
    nombre = (nombre or "").strip()
    correo = normalizar_correo(correo)
    if not nombre:
        raise ErrorUsuario("Escribe el nombre de la persona administradora.")
    if not _PATRON_CORREO.match(correo):
        raise ErrorUsuario("Escribe un correo válido, por ejemplo nombre@negocio.com.")
    validar_contrasena(contrasena)
    if existe_correo(correo):
        raise ErrorUsuario("Ya existe una cuenta con ese correo.")

    usuario = Usuario(nombre=nombre, correo=correo, rol=ROL_ADMINISTRADOR)
    usuario.establecer_contrasena(contrasena)
    db.session.add(usuario)
    db.session.commit()
    return usuario
