"""Ruta /salud para el monitoreo de disponibilidad (RNF-13) y cabeceras de seguridad (A05)."""


def test_salud_responde_ok_sin_datos(cliente):
    respuesta = cliente.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.get_json() == {"estado": "ok"}


def test_cabeceras_de_seguridad(cliente):
    respuesta = cliente.get("/salud")
    assert "default-src 'self'" in respuesta.headers["Content-Security-Policy"]
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers["X-Frame-Options"] == "SAMEORIGIN"
