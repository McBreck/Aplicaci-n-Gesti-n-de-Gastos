"""Interfaz base (sección 11): layout, navegación por rol, accesibilidad y cumplimiento de la CSP."""
import re
from pathlib import Path

import pytest

CARPETA_PLANTILLAS = Path(__file__).resolve().parents[2] / "app" / "templates"


def test_layout_de_la_aplicacion(cliente, crear_usuario, iniciar_sesion):
    crear_usuario()
    iniciar_sesion("prueba.ana@ejemplo.com")
    texto = cliente.get("/").get_data(as_text=True)
    assert '<html lang="es">' in texto
    assert 'class="cg-lateral"' in texto
    assert 'id="menuMovil"' in texto  # offcanvas del celular
    assert 'aria-label="Abrir menú"' in texto
    assert ">PA<" in texto.replace(" ", "").replace("\n", "")  # avatar con iniciales
    assert "Cerrar sesión" in texto
    assert 'aria-current="page"' in texto


def test_navegacion_del_administrador(cliente, crear_admin, iniciar_sesion):
    crear_admin()
    iniciar_sesion("prueba.admin@ejemplo.com")
    texto = cliente.get("/admin/usuarios").get_data(as_text=True)
    assert "Usuarios" in texto
    assert "Mi cuenta" in texto
    assert "Mis gastos" not in texto
    assert 'aria-label="Registrar gasto"' not in texto


def test_assets_locales_sin_cdn(cliente, sesion):
    texto = cliente.get("/login").get_data(as_text=True)
    assert "/static/vendor/bootstrap-5.3.3/css/bootstrap.min.css" in texto
    assert "/static/vendor/bootstrap-5.3.3/js/bootstrap.bundle.min.js" in texto
    assert "/static/css/app.css" in texto
    assert "cdn." not in texto
    for ruta in ("/static/css/app.css", "/static/js/app.js", "/static/img/favicon.svg",
                 "/static/vendor/inter-5.2.8/inter.css"):
        assert cliente.get(ruta).status_code == 200


@pytest.mark.parametrize("plantilla", sorted(CARPETA_PLANTILLAS.rglob("*.html")), ids=lambda p: p.name)
def test_plantillas_sin_scripts_ni_estilos_en_linea(plantilla):
    """CSP default-src 'self': nada de <script> en línea, style= ni manejadores on*."""
    contenido = plantilla.read_text(encoding="utf-8")
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", contenido)
    assert not re.search(r"\sstyle=", contenido)
    assert not re.search(r"\son[a-z]+=", contenido)
    assert "|safe" not in contenido


def test_toast_con_accion(app, cliente, crear_usuario, iniciar_sesion):
    from flask import flash, render_template_string

    crear_usuario()
    iniciar_sesion("prueba.ana@ejemplo.com")
    with app.test_request_context():
        flash({"texto": "Gasto guardado · Incompleto", "accion_url": "/x", "accion_texto": "Completar ahora"}, "aviso")
        html = render_template_string('{% include "componentes/toasts.html" %}')
    assert "Completar ahora" in html
    assert 'data-bs-autohide="false"' in html
    assert "bi-exclamation-triangle" in html


def test_macros_de_estado_y_barra(app):
    from flask import render_template_string

    with app.test_request_context():
        html = render_template_string(
            '{% from "componentes/ui.html" import chip_estado, barra_presupuesto, pildora_categoria %}'
            '{{ chip_estado("Excedida") }}{{ barra_presupuesto(150, "Excedida") }}'
            '{{ pildora_categoria("Alquiler", "#93C5FD") }}'
        )
    assert "cg-chip--excedida" in html and "bi-x-circle" in html and "Excedida" in html
    assert 'data-cg-ancho="100.00"' in html  # la escala se corta en 125 %
    assert 'data-cg-color-texto="#111827"' in html
