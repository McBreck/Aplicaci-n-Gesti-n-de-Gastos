#!/usr/bin/env bash
# =====================================================================================
# Instalación del servidor de ControlGastos en Ubuntu 24.04 LTS (EDT 5.1 y 5.2)
#
# Prepara un VPS recién creado:
#   1. actualizaciones del sistema;
#   2. zona horaria America/Lima;
#   3. usuario "controlgastos", que ejecuta la aplicación y no puede entrar por SSH;
#   4. firewall UFW: solo SSH (22), HTTP (80) y HTTPS (443);
#   5. SSH solo con llave (si tu usuario administrador ya tiene una);
#   6. PostgreSQL 16, que solo escucha en el propio servidor;
#   7. Python 3.11 (Ubuntu 24.04 trae 3.12): con el PPA deadsnakes o con uv;
#   8. Nginx y Certbot.
#
# No descarga el código ni crea la base de datos: eso se hace con la guía
# docs/DESPLIEGUE_HOSTINGER.md. Se puede ejecutar varias veces: cada paso revisa si
# ya está hecho.
#
# Uso, con tu usuario administrador (no como root):
#   sudo bash instalar_servidor.sh
# Python 3.11 con uv en lugar del PPA deadsnakes:
#   sudo METODO_PYTHON=uv bash instalar_servidor.sh
# =====================================================================================
set -euo pipefail

APP_USUARIO="controlgastos"
APP_DIR="/srv/controlgastos"
ZONA_HORARIA="America/Lima"
METODO_PYTHON="${METODO_PYTHON:-deadsnakes}"  # deadsnakes | uv
UV_VERSION="${UV_VERSION:-0.6.0}"
UV_PYTHON_DIR="/opt/uv-python"

paso() { printf '\n==> %s\n' "$*"; }
aviso() { printf '    AVISO: %s\n' "$*"; }

# En WSL (ensayo en una computadora con Windows) no hay firewall ni servidor SSH propios
es_wsl() { grep -qi microsoft /proc/version 2>/dev/null; }

actualizar_sistema() {
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -q
    apt-get upgrade -yq
    apt-get install -yq git curl ca-certificates software-properties-common ufw
}

configurar_zona_horaria() {
    timedatectl set-timezone "$ZONA_HORARIA"
    echo "    $(timedatectl show --property=Timezone --value)"
}

crear_usuario_aplicacion() {
    if id "$APP_USUARIO" >/dev/null 2>&1; then
        echo "    Ya existe."
        return
    fi
    useradd --system --user-group --home-dir "$APP_DIR" --no-create-home \
        --shell /usr/sbin/nologin "$APP_USUARIO"
    echo "    Creado."
}

configurar_firewall() {
    if es_wsl; then
        aviso "WSL detectado (ensayo): se omite el firewall."
        return
    fi
    # Primero se abre SSH para no perder la conexión actual al activar el firewall
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp
    ufw default deny incoming
    ufw default allow outgoing
    ufw --force enable
    ufw status verbose
}

configurar_ssh() {
    if es_wsl || [ ! -d /etc/ssh/sshd_config.d ]; then
        aviso "No hay servidor SSH: se omite."
        return
    fi
    local administrador="${SUDO_USER:-}"
    local llaves="/home/${administrador}/.ssh/authorized_keys"
    if [ -z "$administrador" ] || [ "$administrador" = "root" ] || [ ! -s "$llaves" ]; then
        aviso "Tu usuario administrador aún no tiene una llave SSH en ${llaves}."
        aviso "Se mantiene el acceso con contraseña. Agrega la llave y vuelve a ejecutar el script."
        return
    fi
    cat > /etc/ssh/sshd_config.d/60-controlgastos.conf <<'CONFIG'
# ControlGastos: acceso solo con llave SSH y sin entrar directamente como root
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
CONFIG
    sshd -t
    systemctl try-reload-or-restart ssh
    echo "    Listo: solo se entra con llave y con el usuario ${administrador}."
}

instalar_postgresql() {
    apt-get install -yq postgresql postgresql-contrib
    systemctl enable --now postgresql
    local version
    version="$(runuser -u postgres -- psql -tAc 'SHOW server_version')"
    echo "    PostgreSQL ${version}"
    case "$version" in
        16.*) ;;
        *) aviso "ControlGastos usa PostgreSQL 16 y se instaló la versión ${version}." ;;
    esac
    echo "    listen_addresses = $(runuser -u postgres -- psql -tAc 'SHOW listen_addresses')"
}

instalar_python() {
    if command -v python3.11 >/dev/null 2>&1; then
        echo "    Ya instalado: $(python3.11 --version)"
        return
    fi
    case "$METODO_PYTHON" in
        deadsnakes)
            add-apt-repository -y ppa:deadsnakes/ppa
            apt-get update -q
            apt-get install -yq python3.11 python3.11-venv python3.11-dev
            ;;
        uv)
            if ! command -v uv >/dev/null 2>&1; then
                curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" \
                    | env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh
            fi
            UV_PYTHON_INSTALL_DIR="$UV_PYTHON_DIR" uv python install 3.11
            ln -sf "$(UV_PYTHON_INSTALL_DIR="$UV_PYTHON_DIR" uv python find 3.11)" /usr/local/bin/python3.11
            ;;
        *)
            echo "METODO_PYTHON debe ser deadsnakes o uv." >&2
            exit 1
            ;;
    esac
    python3.11 -m venv --help >/dev/null
    echo "    $(python3.11 --version)"
}

instalar_nginx_y_certbot() {
    apt-get install -yq nginx certbot python3-certbot-nginx
    systemctl enable --now nginx
}

mostrar_resumen() {
    echo "    Zona horaria: $(timedatectl show --property=Timezone --value)"
    echo "    $(runuser -u postgres -- psql -tAc 'SELECT version()' | cut -d, -f1)"
    echo "    $(python3.11 --version)"
    echo "    $(nginx -v 2>&1)"
    echo "    $(certbot --version 2>&1)"
    if ! es_wsl; then
        echo "    Firewall: $(ufw status | head -n 1)"
    fi
    echo
    echo "Servidor listo. Sigue con el paso 5.2 de docs/DESPLIEGUE_HOSTINGER.md."
}

main() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "Ejecuta este script con sudo: sudo bash instalar_servidor.sh" >&2
        exit 1
    fi
    # shellcheck source=/dev/null
    . /etc/os-release
    if [ "${VERSION_ID:-}" != "24.04" ]; then
        aviso "El script está preparado para Ubuntu 24.04 y este sistema es ${PRETTY_NAME:-desconocido}."
    fi

    paso "1/8 Actualizar el sistema"
    actualizar_sistema
    paso "2/8 Zona horaria ${ZONA_HORARIA}"
    configurar_zona_horaria
    paso "3/8 Usuario de la aplicación (${APP_USUARIO})"
    crear_usuario_aplicacion
    paso "4/8 Firewall: SSH, HTTP y HTTPS"
    configurar_firewall
    paso "5/8 SSH solo con llave"
    configurar_ssh
    paso "6/8 PostgreSQL 16"
    instalar_postgresql
    paso "7/8 Python 3.11 (${METODO_PYTHON})"
    instalar_python
    paso "8/8 Nginx y Certbot"
    instalar_nginx_y_certbot
    paso "Resumen"
    mostrar_resumen
}

main "$@"
