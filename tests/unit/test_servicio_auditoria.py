"""AuditoriaService (RNF-12): eventos sin contraseñas, con la IP de la petición y sin commit propio."""
from sqlalchemy import func, select

from app.models import Auditoria
from app.services import auditoria


def test_quita_las_claves_sensibles_en_todos_los_niveles(sesion):
    evento = auditoria.registrar(auditoria.MODIFICAR, "usuario", detalle={
        "nuevo": {"nombre": "PRUEBA Ana", "contrasena": "x", "Password_hash": "y"},
        "historial": [{"clave_temporal": "z", "campo": "correo"}],
        "contraseña": "w",
    })
    assert evento.detalle == {"nuevo": {"nombre": "PRUEBA Ana"}, "historial": [{"campo": "correo"}]}


def test_ip_de_la_peticion(app, sesion):
    assert auditoria.registrar(auditoria.CREAR, "gasto").ip is None  # consola: sin petición
    with app.test_request_context(environ_base={"REMOTE_ADDR": "203.0.113.7"}):
        assert auditoria.registrar(auditoria.CREAR, "gasto").ip == "203.0.113.7"


def test_se_guarda_con_el_commit_de_la_operacion(sesion):
    auditoria.registrar(auditoria.ELIMINAR, "gasto", entidad_id=5)
    sesion.rollback()  # si la operación falla, el evento tampoco queda
    assert sesion.scalar(select(func.count()).select_from(Auditoria)) == 0
    evento = auditoria.registrar(auditoria.ELIMINAR, "gasto", entidad_id=5)
    sesion.commit()
    assert (evento.accion, evento.entidad, evento.entidad_id, evento.detalle) == ("ELIMINAR", "gasto", 5, None)
