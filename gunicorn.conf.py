"""Configuración de Gunicorn.

En desarrollo escucha en 127.0.0.1:8000; en producción GUNICORN_BIND apunta
al socket Unix que usa Nginx (unix:/run/controlgastos/gunicorn.sock).
Gunicorn no funciona en Windows: allí se usa `flask run`.
"""
import os

bind = os.environ.get("GUNICORN_BIND", "127.0.0.1:8000")
workers = 3
timeout = 30
accesslog = "-"
errorlog = "-"
loglevel = "info"
