"""Reglas encapsuladas en los modelos: RN-01 (completitud), RN-05/RN-06 (estado) y Argon2id."""
from datetime import date
from decimal import Decimal

import pytest

from app.models import Categoria, Gasto, MetodoPago, Presupuesto, Usuario
from app.models.presupuesto import estado_presupuesto


def _gasto_completo() -> Gasto:
    return Gasto(
        fecha=date(2026, 10, 1),
        monto=Decimal("190.00"),
        categoria_id=1,
        descripcion="Harina 2 sacos",
        metodo_pago_id=1,
    )


def test_gasto_con_los_cinco_campos_es_completo():
    gasto = _gasto_completo()
    assert gasto.campos_faltantes() == []
    assert gasto.evaluar_completitud() is True
    assert gasto.es_completo is True


def test_gasto_con_solo_fecha_y_monto_lista_los_faltantes():
    gasto = Gasto(fecha=date(2026, 10, 1), monto=Decimal("24.00"))
    assert gasto.campos_faltantes() == ["categoría", "descripción", "método de pago"]
    assert gasto.evaluar_completitud() is False


@pytest.mark.parametrize("descripcion", [None, "", "   "])
def test_descripcion_vacia_cuenta_como_faltante(descripcion):
    gasto = _gasto_completo()
    gasto.descripcion = descripcion
    assert gasto.campos_faltantes() == ["descripción"]


def test_completitud_reconoce_relaciones_asignadas():
    gasto = Gasto(fecha=date(2026, 10, 1), monto=Decimal("5"), descripcion="Pasaje")
    gasto.categoria = Categoria(nombre="Transporte")
    gasto.metodo_pago = MetodoPago(id=1, nombre="Efectivo")
    assert gasto.evaluar_completitud() is True


@pytest.mark.parametrize(
    ("ejecutado", "estado"),
    [
        ("0", "Controlada"),
        ("79.90", "Controlada"),
        ("80.00", "En alerta"),
        ("100.00", "En alerta"),
        ("100.10", "Excedida"),
    ],
)
def test_limites_del_estado_de_presupuesto(ejecutado, estado):
    presupuesto = Presupuesto(monto=Decimal("100.00"))
    assert presupuesto.estado(Decimal(ejecutado)) == estado


def test_estado_con_datos_de_verificacion():
    assert estado_presupuesto(Decimal("550.30"), Decimal("520.00")) == "Excedida"
    assert estado_presupuesto(Decimal("50.00"), Decimal("60.00")) == "En alerta"


def test_estado_con_presupuesto_en_cero():
    assert estado_presupuesto(0, 0) == "Controlada"
    assert estado_presupuesto(Decimal("0.01"), 0) == "Excedida"


def test_contrasena_se_guarda_como_argon2id():
    usuario = Usuario()
    usuario.establecer_contrasena("clave1234")
    assert usuario.password_hash.startswith("$argon2id$")
    assert "clave1234" not in usuario.password_hash
    assert usuario.verificar_contrasena("clave1234") is True
    assert usuario.verificar_contrasena("otra1234") is False
    assert usuario.necesita_rehash() is False


def test_verificar_contrasena_con_hash_invalido():
    usuario = Usuario(password_hash="no-es-un-hash")
    assert usuario.verificar_contrasena("clave1234") is False


def test_cuenta_desactivada_no_esta_activa_para_flask_login():
    assert Usuario(activo=False).is_active is False
    assert Usuario(activo=True).is_active is True
    assert Usuario(rol="administrador").es_administrador is True
