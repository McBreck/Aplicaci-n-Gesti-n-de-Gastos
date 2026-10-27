"""Controladores (blueprints) de ControlGastos."""
from flask import Flask


def registrar_blueprints(app: Flask) -> None:
    from app.blueprints.admin import bp as admin_bp
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.categorias import bp as categorias_bp
    from app.blueprints.dashboard import bp as dashboard_bp
    from app.blueprints.gastos import bp as gastos_bp
    from app.blueprints.presupuesto import bp as presupuesto_bp
    from app.blueprints.reportes import bp as reportes_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(gastos_bp)
    app.register_blueprint(categorias_bp)
    app.register_blueprint(presupuesto_bp)
    app.register_blueprint(reportes_bp)
