"""Esquema inicial de ControlGastos con catálogos (EDT 2.2).

Crea las seis tablas del diseño físico, sus restricciones e índices, y carga
los métodos de pago (RN-12) y la plantilla de categorías (RN-11) con los
colores de la paleta de interfaz (cambio CR-01).

Revision ID: 0001
Revises:
Create Date: 2026-10-26
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

METODOS_PAGO = (
    (1, "Efectivo"),
    (2, "Yape"),
    (3, "Plin"),
    (4, "Transferencia bancaria"),
    (5, "Tarjeta"),
)

CATEGORIAS_PREDETERMINADAS = (
    ("Insumos y materia prima", "#8B7BFF"),
    ("Mercadería", "#FFD166"),
    ("Servicios (luz, agua, gas)", "#7EF0C0"),
    ("Alquiler", "#93C5FD"),
    ("Transporte", "#F9A8D4"),
    ("Sueldos y pagos a terceros", "#FDBA74"),
    ("Mantenimiento", "#BEF264"),
    ("Empaques y envases", "#67E8F9"),
    ("Otros", "#CBD5E1"),
)


def _marca_de_tiempo(nombre: str) -> sa.Column:
    return sa.Column(nombre, sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)


def upgrade():
    op.create_table(
        "usuario",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("correo", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("rol", sa.String(20), server_default="microemprendedor", nullable=False),
        sa.Column("nombre_negocio", sa.String(120), nullable=True),
        sa.Column("rubro", sa.String(60), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("intentos_fallidos", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ultimo_acceso", sa.DateTime(timezone=True), nullable=True),
        _marca_de_tiempo("creado_en"),
        sa.CheckConstraint("rol IN ('microemprendedor', 'administrador')", name=op.f("ck_usuario_rol")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuario")),
        sa.UniqueConstraint("correo", name=op.f("uq_usuario_correo")),
    )

    categoria = op.create_table(
        "categoria",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("nombre", sa.String(60), nullable=False),
        sa.Column("predeterminada", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("color", sa.CHAR(7), server_default="#8B7BFF", nullable=False),
        sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        _marca_de_tiempo("creado_en"),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"],
            name=op.f("fk_categoria_usuario_id_usuario"), ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_categoria")),
    )
    op.create_index(
        "uq_categoria_usuario_nombre", "categoria",
        ["usuario_id", sa.text("lower(nombre)")],
        unique=True, postgresql_where=sa.text("usuario_id IS NOT NULL"),
    )
    op.create_index(
        "uq_categoria_predeterminada", "categoria",
        [sa.text("lower(nombre)")],
        unique=True, postgresql_where=sa.text("usuario_id IS NULL"),
    )

    metodo_pago = op.create_table(
        "metodo_pago",
        sa.Column("id", sa.SmallInteger(), autoincrement=False, nullable=False),
        sa.Column("nombre", sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_metodo_pago")),
        sa.UniqueConstraint("nombre", name=op.f("uq_metodo_pago_nombre")),
    )

    op.create_table(
        "gasto",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=True),
        sa.Column("metodo_pago_id", sa.SmallInteger(), nullable=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        sa.Column("descripcion", sa.String(255), nullable=True),
        sa.Column("es_completo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("eliminado", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        _marca_de_tiempo("creado_en"),
        _marca_de_tiempo("actualizado_en"),
        sa.CheckConstraint("monto > 0", name=op.f("ck_gasto_monto_positivo")),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"],
            name=op.f("fk_gasto_usuario_id_usuario"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"], ["categoria.id"], name=op.f("fk_gasto_categoria_id_categoria"),
        ),
        sa.ForeignKeyConstraint(
            ["metodo_pago_id"], ["metodo_pago.id"], name=op.f("fk_gasto_metodo_pago_id_metodo_pago"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_gasto")),
    )
    op.create_index(
        "ix_gasto_usuario_fecha", "gasto", ["usuario_id", "fecha"],
        postgresql_where=sa.text("eliminado = false"),
    )
    op.create_index(
        "ix_gasto_usuario_categoria", "gasto", ["usuario_id", "categoria_id"],
        postgresql_where=sa.text("eliminado = false"),
    )

    op.create_table(
        "presupuesto",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("categoria_id", sa.Integer(), nullable=False),
        sa.Column("anio", sa.SmallInteger(), nullable=False),
        sa.Column("mes", sa.SmallInteger(), nullable=False),
        sa.Column("monto", sa.Numeric(10, 2), nullable=False),
        _marca_de_tiempo("creado_en"),
        sa.CheckConstraint("anio BETWEEN 2026 AND 2100", name=op.f("ck_presupuesto_anio")),
        sa.CheckConstraint("mes BETWEEN 1 AND 12", name=op.f("ck_presupuesto_mes")),
        sa.CheckConstraint("monto >= 0", name=op.f("ck_presupuesto_monto_no_negativo")),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"],
            name=op.f("fk_presupuesto_usuario_id_usuario"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["categoria_id"], ["categoria.id"], name=op.f("fk_presupuesto_categoria_id_categoria"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_presupuesto")),
        sa.UniqueConstraint("usuario_id", "categoria_id", "anio", "mes", name="uq_presupuesto"),
    )

    op.create_table(
        "auditoria",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("accion", sa.String(20), nullable=False),
        sa.Column("entidad", sa.String(30), nullable=False),
        sa.Column("entidad_id", sa.BigInteger(), nullable=True),
        sa.Column("detalle", postgresql.JSONB(), nullable=True),
        sa.Column("ip", postgresql.INET(), nullable=True),
        _marca_de_tiempo("creado_en"),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"],
            name=op.f("fk_auditoria_usuario_id_usuario"), ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auditoria")),
    )
    op.create_index("ix_auditoria_usuario_fecha", "auditoria", ["usuario_id", "creado_en"])

    # Datos de catálogo
    op.bulk_insert(metodo_pago, [{"id": id_, "nombre": nombre} for id_, nombre in METODOS_PAGO])
    op.bulk_insert(
        categoria,
        [
            {"usuario_id": None, "nombre": nombre, "predeterminada": True, "color": color}
            for nombre, color in CATEGORIAS_PREDETERMINADAS
        ],
    )


def downgrade():
    op.drop_index("ix_auditoria_usuario_fecha", table_name="auditoria")
    op.drop_table("auditoria")
    op.drop_table("presupuesto")
    op.drop_index("ix_gasto_usuario_categoria", table_name="gasto")
    op.drop_index("ix_gasto_usuario_fecha", table_name="gasto")
    op.drop_table("gasto")
    op.drop_table("metodo_pago")
    op.drop_index("uq_categoria_predeterminada", table_name="categoria")
    op.drop_index("uq_categoria_usuario_nombre", table_name="categoria")
    op.drop_table("categoria")
    op.drop_table("usuario")
