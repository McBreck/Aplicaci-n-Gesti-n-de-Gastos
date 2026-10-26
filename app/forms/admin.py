"""Formularios de administración de cuentas (P-08)."""
from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired, Length, Optional


class UsuarioForm(FlaskForm):
    nombre = StringField(
        "Nombre completo",
        validators=[
            DataRequired("Escribe el nombre de la persona."),
            Length(max=100, message="El nombre puede tener hasta 100 caracteres."),
        ],
    )
    correo = StringField(
        "Correo",
        validators=[
            DataRequired("Escribe el correo con el que ingresará."),
            Length(max=120, message="El correo puede tener hasta 120 caracteres."),
        ],
    )
    nombre_negocio = StringField(
        "Nombre del negocio",
        validators=[Optional(), Length(max=120, message="Puede tener hasta 120 caracteres.")],
    )
    rubro = StringField(
        "Rubro",
        validators=[Optional(), Length(max=60, message="Puede tener hasta 60 caracteres.")],
    )


class NuevoUsuarioForm(UsuarioForm):
    contrasena_temporal = StringField(
        "Contraseña temporal",
        validators=[DataRequired("Escribe una contraseña temporal.")],
    )
