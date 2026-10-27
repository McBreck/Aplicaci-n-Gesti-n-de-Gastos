#!/usr/bin/env bash
# =====================================================================================
# Restauración de un respaldo de ControlGastos (RNF-14, EDT 5.2)
#
# Por defecto restaura en una base aparte, "controlgastos_restauracion", para comprobar
# que el respaldo sirve sin tocar la base real.
#
# Uso:
#   sudo bash restaurar_bd.sh            # el respaldo más reciente
#   sudo bash restaurar_bd.sh /var/backups/controlgastos/controlgastos_20261101_023000.dump
#
# Restaurar sobre la base real (solo si se perdieron datos; detiene la aplicación
# mientras tanto y reemplaza TODOS los datos actuales):
#   sudo DESTINO=controlgastos CONFIRMAR=si bash restaurar_bd.sh archivo.dump
# =====================================================================================
set -euo pipefail

CARPETA="${CARPETA:-/var/backups/controlgastos}"
DESTINO="${DESTINO:-controlgastos_restauracion}"
PROPIETARIO="${PROPIETARIO:-controlgastos}"
BASE_REAL="controlgastos"

mas_reciente() {
    find "$CARPETA" -maxdepth 1 -type f -name '*.dump' -printf '%T@ %p\n' 2>/dev/null \
        | sort -rn | head -n 1 | cut -d' ' -f2-
}

mostrar_contenido() {
    local tiene_tablas
    tiene_tablas="$(runuser -u postgres -- psql -d "$DESTINO" -tAc "SELECT to_regclass('public.usuario') IS NOT NULL")"
    if [ "$tiene_tablas" != "t" ]; then
        echo "La base restaurada no tiene las tablas de ControlGastos (respaldo anterior a las migraciones)."
        return
    fi
    runuser -u postgres -- psql -d "$DESTINO" -c "
        SELECT (SELECT count(*) FROM usuario) AS cuentas,
               (SELECT count(*) FROM categoria) AS categorias,
               (SELECT count(*) FROM gasto) AS gastos,
               (SELECT count(*) FROM presupuesto) AS presupuestos,
               (SELECT count(*) FROM auditoria) AS eventos;"
}

main() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "Ejecuta este script con sudo." >&2
        exit 1
    fi
    local archivo="${1:-$(mas_reciente)}"
    if [ -z "$archivo" ] || [ ! -f "$archivo" ]; then
        echo "No encontré el respaldo: ${archivo:-no hay archivos .dump en ${CARPETA}}" >&2
        exit 1
    fi

    local sobre_la_real=0
    if [ "$DESTINO" = "$BASE_REAL" ]; then
        if [ "${CONFIRMAR:-}" != "si" ]; then
            echo "Esto reemplaza todos los datos de la base real. Para continuar agrega CONFIRMAR=si." >&2
            exit 1
        fi
        sobre_la_real=1
        echo "Deteniendo la aplicación..."
        systemctl stop controlgastos
    fi

    echo "Restaurando ${archivo} en la base ${DESTINO}..."
    runuser -u postgres -- dropdb --if-exists "$DESTINO"
    runuser -u postgres -- createdb --owner="$PROPIETARIO" --encoding=UTF8 --template=template0 "$DESTINO"
    runuser -u postgres -- pg_restore --no-owner --role="$PROPIETARIO" --dbname="$DESTINO" "$archivo"

    if [ "$sobre_la_real" -eq 1 ]; then
        systemctl start controlgastos
        echo "Aplicación iniciada de nuevo."
    fi
    echo "Contenido de la base restaurada:"
    mostrar_contenido
    if [ "$sobre_la_real" -eq 0 ]; then
        echo "Prueba terminada. Para borrar la base de prueba: sudo -u postgres dropdb ${DESTINO}"
    fi
}

main "$@"
