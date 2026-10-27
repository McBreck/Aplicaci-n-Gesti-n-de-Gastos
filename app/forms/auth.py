"""Formularios de acceso: inicio de sesión (P-01) y cambio de contraseña (P-09)."""
from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    correo = StringField(
        "Correo",
        validators=[
            DataRequired("Escribe tu correo."),
            Length(max=120, message="El correo puede tener hasta 120 caracteres."),
        ],
    )
    contrasena = PasswordField("Contraseña", validators=[DataRequired("Escribe tu contraseña.")])


class CambioContrasenaForm(FlaskForm):
    contrasena_actual = PasswordField(
        "Contraseña actual", validators=[DataRequired("Escribe tu contraseña actual.")]
    )
    contrasena_nueva = PasswordField(
        "Nueva contraseña", validators=[DataRequired("Escribe la nueva contraseña.")]
    )
    confirmacion = PasswordField(
        "Repite la nueva contraseña", validators=[DataRequired("Repite la nueva contraseña.")]
    )
