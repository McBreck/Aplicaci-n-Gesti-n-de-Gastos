"""Formularios de categorías (P-06). La validación de negocio la hace CategoriaService."""
from flask_wtf import FlaskForm
from wtforms import StringField


class CategoriaForm(FlaskForm):
    nombre = StringField("Nombre")
    color = StringField("Color")


class RenombrarCategoriaForm(FlaskForm):
    nombre = StringField("Nuevo nombre")
