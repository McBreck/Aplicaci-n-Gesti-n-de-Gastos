# Despliegue de ControlGastos en Hostinger (EDT 5.1 a 5.3)

Esta guía publica ControlGastos en un VPS de Hostinger con HTTPS, paso a paso y sin experiencia previa en servidores. Al terminar, la aplicación responde en `https://DOMINIO`, con respaldo diario de la base de datos y reinicio automático si algo falla.

```text
Celular o PC ──HTTPS──▶ Nginx ──socket Unix──▶ Gunicorn (3 workers) ──▶ Flask ──▶ PostgreSQL 16
                  (certificado de Let's Encrypt)   (servicio systemd)              (solo localhost)
```

Todos los pasos se ensayaron en Ubuntu 24.04 (WSL) antes de escribir esta guía. Solo falta lo que necesita el VPS real: el firewall, el SSH, el dominio y el certificado.

## Antes de empezar

**Necesitas:**

- una cuenta de Hostinger con el plan **VPS KVM 1** (1 vCPU, 4 GB de RAM, 50 GB NVMe) y un dominio propio;
- tu computadora con Windows y PowerShell (trae `ssh`, `scp` y `curl.exe`);
- acceso al repositorio de GitHub, que es **privado**;
- unas 2 o 3 horas la primera vez.

**Cómo leer los comandos:**

| En la guía | Cámbialo por |
|---|---|
| `DOMINIO` | Tu dominio, sin `https://` ni `www` (por ejemplo, `midominio.com`) |
| `IP_DEL_VPS` | La dirección IP pública del VPS (la muestra Hostinger) |
| `ADMIN` | El nombre de tu usuario administrador en el servidor (por ejemplo, `mcbreck`) |

- Los bloques dicen dónde se ejecutan: **En tu computadora (PowerShell)** o **En el VPS**.
- `sudo` pide la contraseña de tu usuario administrador.
- Para pegar en la terminal del VPS: clic derecho o Ctrl+Shift+V.
- Al final de cada sección está la lista de **evidencias** que conviene capturar para el documento de la EDT.

> Los nombres de los menús de Hostinger pueden cambiar un poco con el tiempo. Si no encuentras uno, busca la opción equivalente en el panel (hPanel).

---

## 5.1 Servidor VPS

### 5.1.1 Contratar el VPS

1. En hPanel, contrata el plan **VPS KVM 1**.
2. Elige la ubicación del servidor más cercana a Perú entre las que ofrezca Hostinger.
3. Elige como sistema operativo **Ubuntu 24.04 LTS** en su versión "solo sistema operativo" (sin panel de control).
4. Define una contraseña de root larga y guárdala en un gestor de contraseñas.
5. Cuando el VPS esté listo, anota su **IP pública** (`IP_DEL_VPS`).

### 5.1.2 Crear tu llave SSH

La llave SSH reemplaza a la contraseña para entrar al servidor: es más segura y no se puede adivinar.

**En tu computadora (PowerShell):**
```powershell
ssh-keygen -t ed25519 -C "controlgastos-vps"
```
Acepta la ubicación propuesta (Enter) y escribe una frase de contraseña que recuerdes. Luego muestra la llave pública:
```powershell
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub"
```
Copia esa línea completa (empieza con `ssh-ed25519`). En hPanel, entra a la configuración del VPS → **Llaves SSH** → agrega la llave.

> Nunca compartas el archivo `id_ed25519` (sin `.pub`): es tu llave privada.

### 5.1.3 Primer acceso

**En tu computadora (PowerShell):**
```powershell
ssh root@IP_DEL_VPS
```
La primera vez pregunta si confías en el servidor: escribe `yes`. Si entraste, verás algo como `root@srv…:~#`.

### 5.1.4 Crear tu usuario administrador

Trabajar como root es riesgoso. Crea tu propio usuario con permisos de administrador (`sudo`) y la misma llave SSH.

**En el VPS (como root):**
```bash
adduser ADMIN
usermod -aG sudo ADMIN
install -d -m 700 -o ADMIN -g ADMIN /home/ADMIN/.ssh
install -m 600 -o ADMIN -g ADMIN /root/.ssh/authorized_keys /home/ADMIN/.ssh/authorized_keys
```
`adduser` pide una contraseña (la usarás con `sudo`) y unos datos opcionales (Enter para omitirlos).

**Prueba, sin cerrar la sesión de root**, en otra ventana de PowerShell:
```powershell
ssh ADMIN@IP_DEL_VPS
```
Ya dentro, ejecuta `sudo whoami`: debe responder `root`. Si funciona, cierra la sesión de root y sigue con tu usuario.

### 5.1.5 Instalar lo necesario en el servidor

El script `instalar_servidor.sh` actualiza el sistema y configura:

- la zona horaria de Lima;
- el usuario `controlgastos`, que ejecuta la aplicación y no puede entrar por SSH;
- el firewall: solo deja pasar SSH (22), HTTP (80) y HTTPS (443);
- el SSH solo con llave y sin acceso directo de root;
- PostgreSQL 16, Python 3.11, Nginx y Certbot.

**En tu computadora (PowerShell)**, desde la carpeta del proyecto, copia los scripts al servidor:
```powershell
scp -r deploy\scripts ADMIN@IP_DEL_VPS:~/scripts
```

**En el VPS (con tu usuario):**
```bash
sudo bash ~/scripts/instalar_servidor.sh
```
Tarda unos minutos y termina con un resumen como este:
```text
==> Resumen
    Zona horaria: America/Lima
    PostgreSQL 16.x … on x86_64-pc-linux-gnu
    Python 3.11.x
    nginx version: nginx/1.24.0 (Ubuntu)
    certbot 2.9.0
    Firewall: Status: active
```
Python 3.11 se instala con el PPA *deadsnakes*. Si esa opción falla, usa **uv**:
```bash
sudo METODO_PYTHON=uv bash ~/scripts/instalar_servidor.sh
```
El script se puede volver a ejecutar sin problema: solo hace lo que falta.

### 5.1.6 Verificar el servidor

**En el VPS:**
```bash
timedatectl | grep "Time zone"     # America/Lima
sudo ufw status verbose            # 22, 80 y 443 ALLOW; "deny (incoming)" por defecto
```
**En tu computadora (PowerShell)**, confirma que ya no se puede entrar con contraseña ni como root:
```powershell
ssh -o PubkeyAuthentication=no ADMIN@IP_DEL_VPS     # Permission denied (publickey)
ssh root@IP_DEL_VPS                                  # Permission denied
```

> Si el script avisó que tu usuario no tenía llave SSH, todavía se puede entrar con contraseña. Revisa el paso 5.1.4 y vuelve a ejecutar el script.

**Evidencias 5.1:**

- plan KVM 1 con Ubuntu 24.04 en hPanel (oculta datos de pago);
- llave SSH agregada;
- inicio de sesión como `ADMIN`;
- resumen del instalador;
- `sudo ufw status verbose`;
- intento con contraseña rechazado.

---

## 5.2 Base de datos

### 5.2.1 Verificar PostgreSQL 16

**En el VPS:**
```bash
sudo -u postgres psql -c "SHOW server_version;"     # 16.x
sudo -u postgres psql -c "SHOW listen_addresses;"   # localhost
sudo ss -tlnp | grep 5432                           # 127.0.0.1:5432 (solo el propio servidor)
```
`listen_addresses = 'localhost'` es el valor por defecto en Ubuntu: la base no se puede alcanzar desde internet. Si muestra otra cosa, edita `/etc/postgresql/16/main/postgresql.conf`, deja `listen_addresses = 'localhost'` y ejecuta `sudo systemctl restart postgresql`.

### 5.2.2 Crear el rol y la base de la aplicación

1. Genera una contraseña solo con letras y números (otros símbolos rompen la dirección de conexión) y guárdala en tu gestor de contraseñas:
   ```bash
   openssl rand -hex 24
   ```
2. Crea el rol `controlgastos`. Pide la contraseña dos veces y queda sin permisos de superusuario:
   ```bash
   sudo -u postgres createuser --pwprompt controlgastos
   sudo -u postgres psql -c "ALTER ROLE controlgastos SET timezone = 'America/Lima';"
   sudo -u postgres createdb --owner=controlgastos --encoding=UTF8 --template=template0 controlgastos
   ```
3. Prueba la conexión (pide la contraseña):
   ```bash
   psql -h localhost -U controlgastos -d controlgastos -c "SELECT current_user, current_setting('TimeZone');"
   ```
   Respuesta esperada: `controlgastos | America/Lima`.

### 5.2.3 Respaldo y restauración de prueba

`respaldo_bd.sh` guarda un `pg_dump` en `/var/backups/controlgastos` y conserva los 7 más recientes. `restaurar_bd.sh` lo restaura en una base aparte para comprobar que sirve, sin tocar la real.

**En el VPS:**
```bash
sudo bash ~/scripts/respaldo_bd.sh
sudo bash ~/scripts/restaurar_bd.sh
sudo -u postgres dropdb controlgastos_restauracion
```
Como la base todavía está vacía, la restauración termina con "La base restaurada no tiene las tablas de ControlGastos". Es lo esperado: en 5.3.9 se repite la prueba con datos. El respaldo **diario automático** se programa en 5.3.7, cuando el código ya está en el servidor.

**Evidencias 5.2:**

- versión 16 y `listen_addresses = localhost`;
- `ss` mostrando `127.0.0.1:5432`;
- conexión con el rol `controlgastos`;
- respaldo creado y restauración de prueba.

---

## 5.3 Publicación con HTTPS

### 5.3.1 Apuntar el dominio al VPS

Hazlo apenas tengas la IP: el cambio puede tardar desde minutos hasta algunas horas en propagarse.

En hPanel → **Dominios** → tu dominio → **DNS** (registros DNS):

| Tipo | Nombre | Apunta a | TTL |
|---|---|---|---|
| A | `@` | `IP_DEL_VPS` | 3600 |
| CNAME | `www` | `DOMINIO` | 3600 |

- Si ya existe un registro A para `@` (por ejemplo, el de la página de estacionamiento de Hostinger), edítalo en lugar de crear otro.
- Si hay registros **AAAA** que apuntan a otro lugar, bórralos: Certbot fallaría.
- Si el dominio no está en Hostinger, crea los mismos registros donde lo compraste.

**Comprueba en tu computadora (PowerShell):**
```powershell
Resolve-DnsName DOMINIO
Resolve-DnsName www.DOMINIO
```
Ambos deben mostrar `IP_DEL_VPS`.

### 5.3.2 Descargar el código con una llave de despliegue

Como el repositorio es privado, el servidor necesita una **llave de despliegue**: una llave SSH de solo lectura para ese repositorio.

**En el VPS:**
```bash
sudo install -d -m 700 /root/.ssh
sudo ssh-keygen -t ed25519 -N "" -C "controlgastos-vps" -f /root/.ssh/github_controlgastos
sudo cat /root/.ssh/github_controlgastos.pub
```
En GitHub, abre el repositorio → **Settings** → **Deploy keys** → **Add deploy key**:

- título "VPS Hostinger";
- pega la llave;
- deja **sin marcar** "Allow write access".

**En el VPS:**
```bash
sudo tee /root/.ssh/config > /dev/null <<'EOF'
Host github.com
    IdentityFile /root/.ssh/github_controlgastos
    IdentitiesOnly yes
EOF
sudo ssh -T git@github.com
```
Responde `yes` a la pregunta del servidor. Debe decir "You've successfully authenticated, but GitHub does not provide shell access".

Ahora descarga la rama `main` en `/srv/controlgastos`. Copia la dirección SSH desde GitHub → **Code** → **SSH**:
```bash
sudo git clone --branch main git@github.com:McBreck/Aplicaci-n-Gesti-n-de-Gastos.git /srv/controlgastos
```
El código queda a nombre de root: la aplicación solo puede leerlo, no modificarlo.

### 5.3.3 Entorno virtual con Python 3.11

**En el VPS:**
```bash
cd /srv/controlgastos
sudo python3.11 -m venv venv
sudo venv/bin/pip install -r requirements.txt
venv/bin/python --version     # Python 3.11.x
```

### 5.3.4 Archivo `.env`

**En el VPS:**
```bash
cd /srv/controlgastos
sudo install -m 640 -o root -g controlgastos deploy/.env.example .env
python3.11 -c "import secrets; print(secrets.token_hex(32))"
sudo nano .env
```
En el editor:

1. pega el resultado del segundo comando después de `SECRET_KEY=`;
2. cambia `CLAVE` por la contraseña del rol de 5.2.2;
3. guarda con Ctrl+O y Enter, y sal con Ctrl+X.

Comprueba los permisos con `ls -l .env`: debe decir `-rw-r----- 1 root controlgastos`.

### 5.3.5 Base de datos y cuenta de administrador

**En el VPS:**
```bash
cd /srv/controlgastos
sudo venv/bin/flask db upgrade
sudo venv/bin/flask crear-admin
```
`crear-admin` pide el nombre, el correo y la contraseña (mínimo 8 caracteres, con letras y números).

> Usa tu nombre real, **sin** el prefijo `PRUEBA`. El comando `flask demo borrar` elimina todas las cuentas cuyo nombre empieza con PRUEBA, también las de administrador.

### 5.3.6 Servicio con systemd (Gunicorn)

El servicio arranca Gunicorn con 3 workers y lo vuelve a iniciar solo si se detiene.

**En el VPS:**
```bash
cd /srv/controlgastos
sudo install -m 644 deploy/systemd/controlgastos.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now controlgastos
systemctl status controlgastos
```
Debe decir `active (running)` con 4 procesos de Gunicorn: el principal y los 3 workers. Sal con `q`. Comprueba que responde:
```bash
curl --unix-socket /run/controlgastos/gunicorn.sock http://localhost/salud     # {"estado":"ok"}
```

### 5.3.7 Nginx y respaldo diario

**En el VPS** (cambia `midominio.com` por tu dominio en el primer comando):
```bash
cd /srv/controlgastos
sudo sed "s/DOMINIO/midominio.com/g" deploy/nginx/controlgastos.conf | sudo tee /etc/nginx/sites-available/controlgastos > /dev/null
sudo ln -sf /etc/nginx/sites-available/controlgastos /etc/nginx/sites-enabled/controlgastos
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```
`nginx -t` debe terminar con "test is successful". Espera un par de segundos y prueba desde tu computadora:
```powershell
curl.exe http://DOMINIO/salud      # {"estado":"ok"}
```
Todavía no hay certificado, así que `http://DOMINIO/login` redirige a una dirección HTTPS que aún no funciona. Se resuelve en el paso siguiente.

Programa el respaldo diario de las 02:30:
```bash
sudo install -m 644 /srv/controlgastos/deploy/cron/controlgastos-respaldo /etc/cron.d/controlgastos-respaldo
```

### 5.3.8 Certificado HTTPS con Certbot

**En el VPS:**
```bash
sudo certbot --nginx -d DOMINIO -d www.DOMINIO --redirect
```
Certbot pide:

- un correo, para avisarte si el certificado está por vencer;
- aceptar los términos (`Y`);
- si quieres compartir el correo con la EFF (`N` está bien).

Termina con "Successfully deployed certificate". Con `--redirect`, todo el tráfico HTTP pasa a HTTPS con una redirección 301.

El certificado dura 90 días y se renueva solo. Compruébalo:
```bash
systemctl list-timers | grep certbot
sudo certbot renew --dry-run       # "Congratulations, all simulated renewals succeeded"
```

### 5.3.9 Verificación final

**CP-32, en tu computadora (PowerShell):**
```powershell
curl.exe -I http://DOMINIO           # HTTP/1.1 301 Moved Permanently  +  Location: https://DOMINIO/
curl.exe -I http://www.DOMINIO       # 301 hacia https://www.DOMINIO/
curl.exe -I https://DOMINIO/login    # HTTP/1.1 200 OK  +  Strict-Transport-Security: max-age=…
```

**En el navegador:**

1. Abre `https://DOMINIO`, toca el candado y revisa que el certificado sea de Let's Encrypt y esté vigente.
2. Ingresa con tu cuenta de administrador y crea la primera cuenta de microemprendedor.

**Restauración de prueba con datos, en el VPS:**
```bash
sudo bash /srv/controlgastos/deploy/scripts/respaldo_bd.sh
sudo bash /srv/controlgastos/deploy/scripts/restaurar_bd.sh
sudo -u postgres dropdb controlgastos_restauracion
```
La tabla final muestra la cantidad de cuentas, categorías, gastos, presupuestos y eventos copiados.

Con esto también puedes ejecutar CP-32 de [docs/pruebas/4.5_seguridad.md](pruebas/4.5_seguridad.md).

**Evidencias 5.3:**

- registros DNS y `Resolve-DnsName`;
- llave de despliegue en GitHub (sin mostrar la llave);
- `systemctl status controlgastos`;
- `nginx -t`;
- salida de Certbot;
- `certbot renew --dry-run`;
- las tres respuestas de `curl.exe`;
- el candado del navegador con el certificado;
- la pantalla de inicio de sesión en `https://DOMINIO`;
- la restauración con datos.

---

## Despliegues siguientes

Cuando haya cambios aprobados y fusionados en `main`, actualiza el servidor con:

```bash
sudo bash /srv/controlgastos/deploy/scripts/desplegar.sh
```
El script:

1. trae el código;
2. instala dependencias;
3. **respalda la base**;
4. aplica las migraciones;
5. reinicia el servicio;
6. comprueba `/salud`.

Si algo falla, muestra los últimos registros del servicio.

### Despliegue desde GitHub Actions (opcional)

El workflow `.github/workflows/deploy.yml` ejecuta el mismo script desde GitHub con un botón. Está desactivado hasta que lo habilites.

1. **En el VPS**, crea un usuario solo para los despliegues:
   ```bash
   sudo adduser --disabled-password --gecos "" despliegue
   sudo install -d -m 700 -o despliegue -g despliegue /home/despliegue/.ssh
   ```
2. **En tu computadora (PowerShell)**, crea una llave sin frase de contraseña (GitHub no puede escribirla). Presiona Enter cuando la pida:
   ```powershell
   ssh-keygen -t ed25519 -C "github-actions" -f "$env:USERPROFILE\.ssh\controlgastos_actions"
   Get-Content "$env:USERPROFILE\.ssh\controlgastos_actions.pub"
   ```
3. **En el VPS**, autoriza esa llave y permite que `despliegue` ejecute **solo** el script de despliegue como administrador. Cambia `LLAVE_PUBLICA` por la línea copiada:
   ```bash
   echo "LLAVE_PUBLICA" | sudo tee /home/despliegue/.ssh/authorized_keys > /dev/null
   sudo chown despliegue:despliegue /home/despliegue/.ssh/authorized_keys
   sudo chmod 600 /home/despliegue/.ssh/authorized_keys
   echo 'despliegue ALL=(root) NOPASSWD: /usr/bin/bash /srv/controlgastos/deploy/scripts/desplegar.sh' \
     | sudo tee /etc/sudoers.d/controlgastos-despliegue > /dev/null
   sudo chmod 440 /etc/sudoers.d/controlgastos-despliegue
   sudo visudo -c
   ```
4. En GitHub → **Settings** → **Secrets and variables** → **Actions**:
   - en **Secrets**, crea `VPS_HOST` (la IP o el dominio), `VPS_USER` (`despliegue`) y `VPS_SSH_KEY` (el contenido completo del archivo `controlgastos_actions`, sin `.pub`);
   - en **Variables**, crea `DESPLIEGUE_HABILITADO` con el valor `si`.
5. Para desplegar: **Actions** → **Despliegue** → **Run workflow**.

## Mantenimiento

| Tarea | Comando (en el VPS) |
|---|---|
| Ver los registros de la aplicación | `journalctl -u controlgastos -f` (salir con Ctrl+C) |
| Ver los errores de Nginx | `sudo tail -n 50 /var/log/nginx/error.log` |
| Reiniciar la aplicación | `sudo systemctl restart controlgastos` |
| Listar los respaldos | `sudo ls -lh /var/backups/controlgastos` |
| Revisar el registro de los respaldos | `tail /var/log/controlgastos-respaldo.log` |
| Actualizar el sistema (una vez al mes) | `sudo apt update && sudo apt upgrade` |
| Restaurar ante una pérdida de datos | `sudo DESTINO=controlgastos CONFIRMAR=si bash /srv/controlgastos/deploy/scripts/restaurar_bd.sh ARCHIVO.dump` |

- **Monitoreo (RNF-13):** `https://DOMINIO/salud` responde `{"estado":"ok"}` y sirve para un servicio de monitoreo externo.
- **Restauración sobre la base real:** detiene la aplicación, reemplaza **todos** los datos actuales por los del respaldo y la vuelve a iniciar.
- **Copia fuera del servidor:** conviene guardar de vez en cuando un respaldo en otro lugar. Primero cópialo a tu carpeta en el VPS:
  ```bash
  sudo install -m 644 -o ADMIN /var/backups/controlgastos/ARCHIVO.dump ~/
  ```
  Luego, en tu computadora: `scp ADMIN@IP_DEL_VPS:~/ARCHIVO.dump .`

## Solución de problemas frecuentes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| **502 Bad Gateway** | La aplicación no está corriendo o no arrancó | `systemctl status controlgastos` y `journalctl -u controlgastos -n 50`. Errores típicos: "Falta SECRET_KEY" (revisa `.env`), `password authentication failed` (la contraseña de `DATABASE_URL` no coincide con la del rol). |
| 502 con "Permission denied" en `/var/log/nginx/error.log` | Permisos del socket | `ls -la /run/controlgastos/` debe mostrar `srwxrwx--- controlgastos www-data gunicorn.sock`. Revisa que el servicio tenga `Group=www-data` y reinícialo. |
| 404 de Nginx justo después de recargarlo | La recarga tarda un instante | Espera 2 segundos y vuelve a probar. |
| Los estilos no cargan (404 o 403 en `/static/`) | La ruta del `alias` | `ls /srv/controlgastos/app/static/css/app.css`. La línea del `alias` debe terminar en `/`. |
| `flask db upgrade` falla con "permission denied for schema public" | La base no es del rol `controlgastos` | Vuelve a crearla con `--owner=controlgastos` (5.2.2). |
| Fechas u horas corridas | Zona horaria | `timedatectl` debe mostrar America/Lima. La aplicación siempre calcula "hoy" en hora de Lima. |
| Certbot no obtiene el certificado | El DNS aún no apunta al VPS, el puerto 80 está cerrado o hay un registro AAAA incorrecto | `Resolve-DnsName DOMINIO` y `sudo ufw status`. Espera la propagación y repite. |
| "El formulario expiró por seguridad" en todos los formularios | Cambió la `SECRET_KEY` o el sitio se abrió con `http://` | Recarga la página e ingresa por `https://DOMINIO`. |
| No puedes entrar por SSH | Firewall o llave | Usa la consola web del VPS en hPanel. Revisa `sudo ufw status` y `/etc/ssh/sshd_config.d/60-controlgastos.conf`. |
| El disco se llena | Registros del sistema | `df -h`; `sudo journalctl --vacuum-time=14d`. Los respaldos ya se limitan a 7. |

## Archivos del despliegue

| Archivo | Para qué sirve |
|---|---|
| `deploy/scripts/instalar_servidor.sh` | Prepara el VPS (5.1) |
| `deploy/scripts/respaldo_bd.sh` | Respaldo de la base; conserva 7 (5.2) |
| `deploy/scripts/restaurar_bd.sh` | Restauración de prueba o real (5.2) |
| `deploy/cron/controlgastos-respaldo` | Respaldo diario a las 02:30 (5.3.7) |
| `deploy/.env.example` | Variables de producción (5.3.4) |
| `deploy/systemd/controlgastos.service` | Servicio de Gunicorn (5.3.6) |
| `deploy/nginx/controlgastos.conf` | Sitio de Nginx; Certbot agrega el HTTPS (5.3.7) |
| `deploy/scripts/desplegar.sh` | Actualiza la aplicación en el servidor |
| `.github/workflows/deploy.yml` | Despliegue manual desde GitHub (opcional) |
| `gunicorn.conf.py` | Gunicorn: socket de `GUNICORN_BIND`, 3 workers, 30 s de espera, registros en journald |
