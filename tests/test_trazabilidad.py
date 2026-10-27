"""Trazabilidad (docs/pruebas): cada caso de prueba automatizable tiene pruebas con su código.

Las pruebas de cada caso se llaman test_cpNN_... y se ejecutan con `pytest -k cpNN -v`.
CP-33 (responsivo) y CP-34 (SUS) son manuales: docs/pruebas/4.6_responsivo_y_sus.md.
"""
import re
from pathlib import Path

CARPETA_PRUEBAS = Path(__file__).parent
CASOS_AUTOMATIZABLES = [f"CP-{numero:02d}" for numero in range(1, 33)]


def test_cada_caso_de_prueba_tiene_pruebas_automatizadas():
    codigos = set()
    for archivo in CARPETA_PRUEBAS.rglob("test_*.py"):
        codigos.update(re.findall(r"^def test_cp(\d{2})_", archivo.read_text(encoding="utf-8"), re.MULTILINE))
    faltantes = [caso for caso in CASOS_AUTOMATIZABLES if caso[3:] not in codigos]
    assert not faltantes, f"Casos de prueba sin pruebas automatizadas: {faltantes}"
