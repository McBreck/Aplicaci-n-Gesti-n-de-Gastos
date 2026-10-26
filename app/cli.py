"""Comandos de consola de ControlGastos (`flask <comando>`)."""
import click
from flask import Flask
from flask.cli import with_appcontext

from app.services import usuario as usuario_service


def registrar_comandos(app: Flask) -> None:
    app.cli.add_command(crear_admin)


@click.command("crear-admin")
@click.option("--nombre", prompt="Nombre completo", help="Nombre de la persona administradora.")
@click.option("--correo", prompt="Correo", help="Correo con el que ingresará.")
@click.password_option(
    "--contrasena",
    prompt="Contraseña",
    confirmation_prompt="Repite la contraseña",
    help="Mínimo 8 caracteres, con letras y números.",
)
@with_appcontext
def crear_admin(nombre: str, correo: str, contrasena: str) -> None:
    """Crea una cuenta de administrador."""
    try:
        usuario = usuario_service.crear_administrador(nombre, correo, contrasena)
    except usuario_service.ErrorUsuario as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Cuenta de administrador creada: {usuario.correo}")
