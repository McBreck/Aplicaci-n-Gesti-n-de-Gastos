"""Formulario del gasto (P-03 y registro rápido).

Solo recoge los datos y valida el token CSRF; las reglas RN-02 a RN-04 las
aplica GastoService para que haya una sola fuente de validación.
"""
from flask_wtf import FlaskForm
from wtforms import StringField

CAMPOS = ("monto", "fecha", "categoria_id", "metodo_pago_id", "descripcion")


class GastoForm(FlaskForm):
    monto = StringField("Monto")
    fecha = StringField("Fecha")
    categoria_id = StringField("Categoría")
    metodo_pago_id = StringField("Método de pago")
    descripcion = StringField("Descripción")

    def datos(self) -> dict:
        return {campo: self[campo].data or "" for campo in CAMPOS}
