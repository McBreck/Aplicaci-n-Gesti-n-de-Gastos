"""Comandos de consola de ControlGastos (`flask <comando>`)."""
import click
from flask import Flask
from flask.cli import AppGroup, with_appcontext

from app import demo
from app.services import usuario as usuario_service
from app.services.formato import fecha, hoy_lima, mes_anio, unir_lista

grupo_demo = AppGroup("demo", help="Datos de demostración PRUEBA (nunca son resultados de la investigación).")


def registrar_comandos(app: Flask) -> None:
    app.cli.add_command(crear_admin)
    app.cli.add_command(grupo_demo)


def _cantidad(numero: int, singular: str, plural: str) -> str:
    return f"{numero} {singular if numero == 1 else plural}"


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


@grupo_demo.command("crear")
@click.password_option(
    "--contrasena",
    prompt="Contraseña de la cuenta de demostración",
    confirmation_prompt="Repite la contraseña",
    help="Mínimo 8 caracteres, con letras y números.",
)
def demo_crear(contrasena: str) -> None:
    """Crea la cuenta "PRUEBA Panadería" con 60 días de gastos y presupuestos."""
    try:
        resumen = demo.crear(contrasena, hoy_lima())
    except (demo.ErrorDemo, usuario_service.ErrorUsuario) as error:
        raise click.ClickException(str(error)) from error
    click.echo("Cuenta de demostración creada.")
    click.echo(f"  Correo: {resumen.correo}")
    click.echo(
        f"  Gastos: {resumen.gastos} del {fecha(resumen.desde)} al {fecha(resumen.hasta)}"
        f" ({_cantidad(resumen.incompletos, 'incompleto', 'incompletos')})"
    )
    click.echo(f"  Presupuestos: {resumen.presupuestos} ({unir_lista([mes_anio(mes) for mes in resumen.meses])})")
    click.echo("Ingresa con ese correo y la contraseña que elegiste. Para borrarla: flask demo borrar")


def _mes_de_rendimiento(_contexto, _parametro, valor):
    """Valida --mes antes de pedir la contraseña."""
    try:
        return demo.mes_de_rendimiento(valor, hoy_lima())
    except demo.ErrorDemo as error:
        raise click.ClickException(str(error)) from error


@grupo_demo.command("rendimiento")
@click.option(
    "--mes", callback=_mes_de_rendimiento, help="Mes de los gastos, como AAAA-MM. Por defecto, el mes anterior."
)
@click.password_option(
    "--contrasena",
    prompt="Contraseña de la cuenta de rendimiento",
    confirmation_prompt="Repite la contraseña",
    help="Mínimo 8 caracteres, con letras y números.",
)
def demo_rendimiento(mes, contrasena: str) -> None:
    """Crea la cuenta "PRUEBA Rendimiento" con 500 gastos en un mes (CP-28)."""
    try:
        resumen = demo.crear_rendimiento(contrasena, mes, hoy_lima())
    except (demo.ErrorDemo, usuario_service.ErrorUsuario) as error:
        raise click.ClickException(str(error)) from error
    click.echo("Cuenta de rendimiento creada.")
    click.echo(f"  Correo: {resumen.correo}")
    click.echo(
        f"  Gastos: {resumen.gastos} del {fecha(resumen.desde)} al {fecha(resumen.hasta)}"
        f" ({_cantidad(resumen.incompletos, 'incompleto', 'incompletos')})"
    )
    click.echo(f"Para CP-28, genera el reporte mensual de {mes_anio(mes)} (docs/pruebas/4.4_rendimiento.md).")


@grupo_demo.command("borrar")
@click.option("--si", is_flag=True, help="Borra sin pedir confirmación.")
def demo_borrar(si: bool) -> None:
    """Borra por completo las cuentas cuyo nombre empieza con PRUEBA y todos sus datos."""
    cuentas = demo.cuentas_prueba()
    if not cuentas:
        click.echo("No hay datos PRUEBA para borrar.")
        return
    verbo = "Se borrará" if len(cuentas) == 1 else "Se borrarán"
    click.echo(
        f"{verbo} {_cantidad(len(cuentas), 'cuenta PRUEBA', 'cuentas PRUEBA')} con sus gastos, "
        "presupuestos, categorías y eventos de la bitácora:"
    )
    for cuenta in cuentas:
        click.echo(f"  - {cuenta.nombre} ({cuenta.correo})")
    if not si:
        respuesta = click.prompt(
            "¿Continuar? (s/n)", type=click.Choice(["s", "n"], case_sensitive=False), default="n", show_choices=False
        )
        if respuesta.lower() != "s":
            click.echo("No se borró nada.")
            return
    resumen = demo.borrar()
    click.echo(
        "Datos PRUEBA borrados: "
        + unir_lista([
            _cantidad(resumen.cuentas, "cuenta", "cuentas"),
            _cantidad(resumen.gastos, "gasto", "gastos"),
            _cantidad(resumen.presupuestos, "presupuesto", "presupuestos"),
            _cantidad(resumen.categorias, "categoría", "categorías"),
            _cantidad(resumen.eventos, "evento de la bitácora", "eventos de la bitácora"),
        ])
        + "."
    )
