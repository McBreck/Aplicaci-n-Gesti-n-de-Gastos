"""Punto de entrada WSGI para Gunicorn (`wsgi:app`) y para el comando `flask`."""
from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402  (después de cargar .env)

app = create_app()
