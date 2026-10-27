#!/usr/bin/env bash
# =====================================================================================
# Respaldo de la base de datos de ControlGastos (RNF-14, EDT 5.2)
#
# Guarda un pg_dump en formato personalizado (-Fc) en /var/backups/controlgastos y
# conserva los 7 respaldos más recientes. El cron deploy/cron/controlgastos-respaldo
# lo ejecuta todos los días a las 02:30, hora de Lima.
#
# Uso manual:
#   sudo bash /srv/controlgastos/deploy/scripts/respaldo_bd.sh
# =====================================================================================
set -euo pipefail

BASE="${BASE:-controlgastos}"
DESTINO="${DESTINO:-/var/backups/controlgastos}"
CONSERVAR="${CONSERVAR:-7}"

main() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "Ejecuta este script con sudo." >&2
        exit 1
    fi
    # Solo el usuario postgres puede leer los respaldos
    install -d -m 700 -o postgres -g postgres "$DESTINO"

    local archivo
    archivo="${DESTINO}/${BASE}_$(date +%Y%m%d_%H%M%S).dump"
    runuser -u postgres -- pg_dump --format=custom --file="$archivo" "$BASE"

    # Borra los más antiguos y deja los CONSERVAR más recientes
    find "$DESTINO" -maxdepth 1 -type f -name "${BASE}_*.dump" -printf '%T@ %p\n' \
        | sort -rn | tail -n +"$((CONSERVAR + 1))" | cut -d' ' -f2- | xargs -r rm -f --

    local cantidad
    cantidad="$(find "$DESTINO" -maxdepth 1 -type f -name "${BASE}_*.dump" | wc -l)"
    echo "$(date '+%d/%m/%Y %H:%M') Respaldo creado: ${archivo} ($(du -h "$archivo" | cut -f1)). Respaldos guardados: ${cantidad}."
}

main "$@"
