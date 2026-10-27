#!/usr/bin/env bash
# =====================================================================================
# Despliegue de una nueva versión de ControlGastos en el VPS (EDT 5.3)
#
#   1. trae el código de la rama main;
#   2. instala las dependencias de requirements.txt;
#   3. respalda la base de datos antes de migrar;
#   4. aplica las migraciones (flask db upgrade);
#   5. reinicia el servicio;
#   6. comprueba que /salud responde.
#
# Uso, con el usuario administrador:
#   sudo bash /srv/controlgastos/deploy/scripts/desplegar.sh
# Otra rama (por ejemplo, para probar develop):
#   sudo RAMA=develop bash /srv/controlgastos/deploy/scripts/desplegar.sh
# =====================================================================================
set -euo pipefail

APP_DIR="/srv/controlgastos"
RAMA="${RAMA:-main}"
SOCKET="/run/controlgastos/gunicorn.sock"

paso() { printf '\n==> %s\n' "$*"; }

comprobar_salud() {
    local respuesta
    for _ in $(seq 1 20); do
        if respuesta="$(curl -fsS --unix-socket "$SOCKET" http://localhost/salud 2>/dev/null)"; then
            echo "    /salud: ${respuesta}"
            return 0
        fi
        sleep 1
    done
    return 1
}

# Todo el trabajo está dentro de main(): bash lee la función completa antes de
# ejecutarla, así el script no se rompe si git pull lo actualiza mientras corre.
main() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "Ejecuta este script con sudo." >&2
        exit 1
    fi
    cd "$APP_DIR"

    paso "1/6 Código de la rama ${RAMA}"
    git fetch --prune origin
    git checkout --quiet "$RAMA"
    git pull --ff-only origin "$RAMA"
    git log -1 --format='    %h %s (%an, %ad)' --date=format:'%d/%m/%Y %H:%M'

    paso "2/6 Dependencias"
    venv/bin/pip install --quiet --disable-pip-version-check -r requirements.txt

    paso "3/6 Respaldo de la base antes de migrar"
    bash "${APP_DIR}/deploy/scripts/respaldo_bd.sh"

    paso "4/6 Migraciones"
    venv/bin/flask db upgrade

    paso "5/6 Reinicio del servicio"
    systemctl restart controlgastos

    paso "6/6 Comprobación"
    if ! comprobar_salud; then
        echo "La aplicación no respondió en /salud. Últimos registros del servicio:" >&2
        journalctl -u controlgastos -n 40 --no-pager >&2
        exit 1
    fi
    echo
    echo "Despliegue completo."
}

main "$@"
