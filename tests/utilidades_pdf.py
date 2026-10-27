"""Lee el texto de los PDF de ReportLab para verificar su contenido en las pruebas.

ReportLab codifica cada flujo en ASCII85 + Flate y escribe las tildes como
escapes octales (\\355 = í); aquí se revierte todo con la biblioteca estándar.
"""
import base64
import re
import zlib


def texto_pdf(contenido: bytes) -> str:
    textos = []
    for flujo in re.findall(rb"stream\r?\n(.*?)endstream", contenido, re.S):
        datos = flujo.strip()
        if datos.endswith(b"~>"):
            datos = base64.a85decode(datos[:-2], adobe=False, ignorechars=b" \t\n\r\x0b")
        try:
            datos = zlib.decompress(datos)
        except zlib.error:
            pass
        # Une los trozos consecutivos de una línea: "(Pan & Café <) Tj (Norte) Tj" → "(Pan & Café <Norte) Tj"
        datos = re.sub(rb"(?<!\\)\)\s*Tj\s*\(", b"", datos)
        datos = re.sub(rb"\\([0-7]{3})", lambda m: bytes([int(m.group(1), 8)]), datos)
        textos.append(datos.replace(rb"\(", b"(").replace(rb"\)", b")").decode("latin-1"))
    return "\n".join(textos)
