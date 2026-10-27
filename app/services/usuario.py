"""UsuarioService: creación y mantenimiento de cuentas (RF-04, RN-11)."""
import re
import secrets

from sqlalchemy import func, select

from app.extensions import db
from app.models import Categoria, Usuario
from app.models.usuario import ROL_ADMINISTRADOR, ROL_MICROEMPRENDEDOR
from app.services import auditoria

ENTIDAD = "usuario"
LONGITUD_MINIMA_CONTRASENA = 8
LONGITUD_CONTRASENA_TEMPORAL = 10
MENSAJE_POLITICA_CONTRASENA = (
    "La contraseña debe tener al menos 8 caracteres e incluir letras y números."
)
MENSAJE_CORREO_DUPLICADO = "Ya existe una cuenta con ese correo."
# Sin caracteres que se confunden al dictarlos (0/O, 1/l/I)
_ALFABETO_TEMPORAL = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CAMPOS_AUDITADOS = ("nombre", "correo", "nombre_negocio", "rubro")


class ErrorUsuario(Exception):
    """Error de negocio con un mensaje listo para mostrar y el campo que lo causó."""

    def __init__(self, mensaje: str, campo: str | None = None):
        super().__init__(mensaje)
        self.campo = campo


class CorreoDuplicado(ErrorUsuario):
    """El correo ya pertenece a otra cuenta (conflicto, RF-04)."""


def validar_contrasena(contrasena: str) -> None:
    """Política de RF-03: mínimo 8 caracteres, con letras y números."""
    contrasena = contrasena or ""
    tiene_letra = any(caracter.isalpha() for caracter in contrasena)
    tiene_numero = any(caracter.isdigit() for caracter in contrasena)
    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA or not (tiene_letra and tiene_numero):
        raise ErrorUsuario(MENSAJE_POLITICA_CONTRASENA, campo="contrasena")


def generar_contrasena_temporal() -> str:
    while True:
        contrasena = "".join(
            secrets.choice(_ALFABETO_TEMPORAL) for _ in range(LONGITUD_CONTRASENA_TEMPORAL)
        )
        try:
            validar_contrasena(contrasena)
        except ErrorUsuario:
            continue
        return contrasena


def normalizar_correo(correo: str) -> str:
    return (correo or "").strip().lower()


def buscar_por_correo(correo: str) -> Usuario | None:
    consulta = select(Usuario).where(func.lower(Usuario.correo) == normalizar_correo(correo))
    return db.session.scalar(consulta)


def existe_correo(correo: str, excepto_id: int | None = None) -> bool:
    usuario = buscar_por_correo(correo)
    return usuario is not None and usuario.id != excepto_id


def listar_cuentas() -> list[Usuario]:
    """Cuentas de microemprendedores (las de administrador se gestionan por consola)."""
    consulta = (
        select(Usuario)
        .where(Usuario.rol == ROL_MICROEMPRENDEDOR)
        .order_by(func.lower(Usuario.nombre))
    )
    return list(db.session.scalars(consulta))


def obtener_cuenta(id_usuario: int) -> Usuario | None:
    usuario = db.session.get(Usuario, id_usuario)
    if usuario is None or usuario.rol != ROL_MICROEMPRENDEDOR:
        return None
    return usuario


def _limpiar_datos(nombre, correo, nombre_negocio=None, rubro=None, excepto_id=None) -> dict:
    datos = {
        "nombre": (nombre or "").strip(),
        "correo": normalizar_correo(correo),
        "nombre_negocio": (nombre_negocio or "").strip() or None,
        "rubro": (rubro or "").strip() or None,
    }
    if not datos["nombre"]:
        raise ErrorUsuario("Escribe el nombre de la persona.", campo="nombre")
    if not _PATRON_CORREO.match(datos["correo"]):
        raise ErrorUsuario("Escribe un correo válido, por ejemplo nombre@negocio.com.", campo="correo")
    if existe_correo(datos["correo"], excepto_id=excepto_id):
        raise CorreoDuplicado(MENSAJE_CORREO_DUPLICADO, campo="correo")
    return datos


def copiar_categorias_predeterminadas(usuario: Usuario) -> None:
    """RN-11: copia la plantilla a la cuenta nueva con predeterminada = TRUE."""
    plantilla = db.session.scalars(
        select(Categoria)
        .where(Categoria.usuario_id.is_(None), Categoria.activa.is_(True))
        .order_by(Categoria.id)
    )
    for categoria in plantilla:
        db.session.add(
            Categoria(
                usuario_id=usuario.id,
                nombre=categoria.nombre,
                color=categoria.color,
                predeterminada=True,
            )
        )


def crear_usuario(*, nombre, correo, nombre_negocio, rubro, contrasena_temporal, actor) -> Usuario:
    """Alta de una cuenta de microemprendedor por el administrador (RF-04)."""
    datos = _limpiar_datos(nombre, correo, nombre_negocio, rubro)
    validar_contrasena(contrasena_temporal)

    usuario = Usuario(rol=ROL_MICROEMPRENDEDOR, **datos)
    usuario.establecer_contrasena(contrasena_temporal)
    db.session.add(usuario)
    db.session.flush()
    copiar_categorias_predeterminadas(usuario)
    auditoria.registrar(
        auditoria.CREAR, ENTIDAD, usuario_id=actor.id, entidad_id=usuario.id, detalle={"nuevo": datos}
    )
    db.session.commit()
    return usuario


def editar_usuario(usuario: Usuario, *, nombre, correo, nombre_negocio, rubro, actor) -> None:
    datos = _limpiar_datos(nombre, correo, nombre_negocio, rubro, excepto_id=usuario.id)
    anterior = {campo: getattr(usuario, campo) for campo in _CAMPOS_AUDITADOS}
    cambios = {campo: valor for campo, valor in datos.items() if anterior[campo] != valor}
    if not cambios:
        return
    for campo, valor in cambios.items():
        setattr(usuario, campo, valor)
    auditoria.registrar(
        auditoria.MODIFICAR,
        ENTIDAD,
        usuario_id=actor.id,
        entidad_id=usuario.id,
        detalle={"anterior": {campo: anterior[campo] for campo in cambios}, "nuevo": cambios},
    )
    db.session.commit()


def cambiar_estado(usuario: Usuario, actor) -> bool:
    """Activa o desactiva la cuenta y devuelve el nuevo estado."""
    usuario.activo = not usuario.activo
    accion = auditoria.ACTIVAR if usuario.activo else auditoria.DESACTIVAR
    auditoria.registrar(accion, ENTIDAD, usuario_id=actor.id, entidad_id=usuario.id)
    db.session.commit()
    return usuario.activo


def restablecer_contrasena(usuario: Usuario, actor) -> str:
    """Asigna una contraseña temporal, quita el bloqueo y la devuelve para mostrarla una vez."""
    contrasena = generar_contrasena_temporal()
    usuario.establecer_contrasena(contrasena)
    usuario.intentos_fallidos = 0
    usuario.bloqueado_hasta = None
    auditoria.registrar(auditoria.RESTABLECER, ENTIDAD, usuario_id=actor.id, entidad_id=usuario.id)
    db.session.commit()
    return contrasena


def crear_administrador(nombre: str, correo: str, contrasena: str) -> Usuario:
    """Cuenta de administrador creada con `flask crear-admin`."""
    datos = _limpiar_datos(nombre, correo)
    validar_contrasena(contrasena)

    usuario = Usuario(rol=ROL_ADMINISTRADOR, nombre=datos["nombre"], correo=datos["correo"])
    usuario.establecer_contrasena(contrasena)
    db.session.add(usuario)
    db.session.flush()
    auditoria.registrar(
        auditoria.CREAR,
        ENTIDAD,
        entidad_id=usuario.id,
        detalle={"nuevo": {"nombre": usuario.nombre, "correo": usuario.correo, "rol": usuario.rol}},
    )
    db.session.commit()
    return usuario
