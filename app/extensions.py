"""Instancias de las extensiones de Flask, inicializadas en create_app().

Talisman no está aquí: guarda su configuración en la instancia, así que
create_app() crea una por aplicación (ver app/__init__.py).
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Nombres estables para restricciones e índices (las migraciones dependen de ellos)
CONVENCION_NOMBRES = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


db = SQLAlchemy(model_class=Base)
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address)
