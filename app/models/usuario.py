"""Modelo Usuario: cuentas de microemprendedores y de administradores."""
from datetime import datetime

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from flask_login import UserMixin
from sqlalchemy import CheckConstraint, DateTime, SmallInteger, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.extensions import db, login_manager

ROL_MICROEMPRENDEDOR = "microemprendedor"
ROL_ADMINISTRADOR = "administrador"

# Argon2id con los parámetros por defecto de argon2-cffi (RNF-07, OWASP A02)
_hasher = PasswordHasher()


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"
    __table_args__ = (
        CheckConstraint("rol IN ('microemprendedor', 'administrador')", name="rol"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    correo: Mapped[str] = mapped_column(String(120), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20), server_default=ROL_MICROEMPRENDEDOR)
    nombre_negocio: Mapped[str | None] = mapped_column(String(120))
    rubro: Mapped[str | None] = mapped_column(String(60))
    activo: Mapped[bool] = mapped_column(server_default=text("true"))
    intentos_fallidos: Mapped[int] = mapped_column(SmallInteger, server_default=text("0"))
    bloqueado_hasta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_acceso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def is_active(self) -> bool:
        """Flask-Login no permite iniciar sesión con una cuenta desactivada."""
        return bool(self.activo)

    @property
    def es_administrador(self) -> bool:
        return self.rol == ROL_ADMINISTRADOR

    def establecer_contrasena(self, contrasena: str) -> None:
        self.password_hash = _hasher.hash(contrasena)

    def verificar_contrasena(self, contrasena: str) -> bool:
        try:
            return _hasher.verify(self.password_hash, contrasena)
        except (VerificationError, InvalidHashError):
            return False

    def necesita_rehash(self) -> bool:
        """True si el hash se generó con parámetros de Argon2 distintos a los actuales."""
        return _hasher.check_needs_rehash(self.password_hash)

    def __repr__(self) -> str:
        return f"<Usuario {self.id} {self.correo}>"


@login_manager.user_loader
def cargar_usuario(id_usuario: str) -> Usuario | None:
    """Una cuenta desactivada pierde la sesión en su siguiente petición (RF-04)."""
    usuario = db.session.get(Usuario, int(id_usuario))
    return usuario if usuario is not None and usuario.activo else None
