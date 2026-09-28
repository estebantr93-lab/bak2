#!/usr/bin/env bash
# Instalación del SGR en una instancia EC2 de AWS Academy.
# Sistemas: Amazon Linux 2023 (usuario ec2-user) o Ubuntu Server 24.04 LTS (usuario ubuntu).
# Uso (en la instancia, con el usuario por defecto):
#   curl -O <url-cruda-de-este-archivo>   (o copiarlo con scp)
#   DEMO_PASSWORD='<clave-nueva>' bash setup_ec2.sh <url-del-repositorio> <rama> [--db-local]
#
# DEMO_PASSWORD (opcional) queda en el .env y es la contraseña de las cuentas de demostración;
# si no se entrega, seed_data genera contraseñas aleatorias y las muestra una sola vez.
#
# --db-local instala MariaDB 10.11 en la misma instancia (útil si el Learner Lab no ofrece
# RDS MySQL 8.4 / MariaDB 10.11, que son las versiones mínimas de Django 6.1).
# Sin --db-local se usa RDS: complete DB_HOST, DB_USER y DB_PASSWORD en /srv/sgr/.env.
set -euo pipefail

REPO_URL="${1:?Indique la URL del repositorio}"
RAMA="${2:-main}"
DB_LOCAL="${3:-}"
APP_DIR=/srv/sgr
APP_USER="$(id -un)"

echo "==> Paquetes del sistema"
if command -v dnf >/dev/null; then
    # Amazon Linux 2023: python3 es 3.9, Django 6.1 necesita 3.12. nginx corre con el grupo nginx.
    PYTHON=python3.12
    WEB_GROUP=nginx
    sudo dnf install -y python3.12 python3.12-devel gcc pkgconf git nginx
    # Cabeceras para compilar mysqlclient (el nombre del paquete cambia según la versión de AL2023).
    sudo dnf install -y mariadb1011-devel || sudo dnf install -y mariadb-connector-c-devel
    if [[ "$DB_LOCAL" == "--db-local" ]]; then
        sudo dnf install -y mariadb1011-server
        sudo systemctl enable --now mariadb
    fi
else
    # Ubuntu 24.04: python3 ya es 3.12. nginx corre con el grupo www-data.
    PYTHON=python3
    WEB_GROUP=www-data
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-venv python3-dev build-essential pkg-config \
        libmariadb-dev nginx git
    if [[ "$DB_LOCAL" == "--db-local" ]]; then
        sudo apt-get install -y mariadb-server
        sudo systemctl enable --now mariadb
    fi
fi
"$PYTHON" -c 'import sys; assert sys.version_info >= (3, 12), "Se necesita Python 3.12 o superior"'

echo "==> Código en $APP_DIR (rama $RAMA)"
sudo mkdir -p "$APP_DIR"
sudo chown "$APP_USER:$WEB_GROUP" "$APP_DIR"
if [[ -d "$APP_DIR/.git" ]]; then
    git -C "$APP_DIR" fetch origin "$RAMA" && git -C "$APP_DIR" checkout "$RAMA" && git -C "$APP_DIR" pull origin "$RAMA"
else
    git clone --branch "$RAMA" "$REPO_URL" "$APP_DIR"
fi
cd "$APP_DIR"

echo "==> Entorno virtual y dependencias"
"$PYTHON" -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [[ ! -f .env ]]; then
    echo "==> Creando .env de producción (revíselo antes de continuar)"
    cp .env.example .env
    SECRET=$(.venv/bin/python -c "from django.core.management.utils import get_random_secret_key as g; print(g())")
    IP=$(curl -s --max-time 3 http://checkip.amazonaws.com || echo "")
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET}|" .env
    sed -i "s|^DEBUG=.*|DEBUG=False|" .env
    sed -i "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=localhost,127.0.0.1,${IP}|" .env
    sed -i "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=http://${IP}|" .env
    if [[ -n "${DEMO_PASSWORD:-}" ]]; then
        # Se escapan &, | y \ para que sed no altere claves con símbolos.
        CLAVE_ESC=$(printf '%s' "$DEMO_PASSWORD" | sed 's/[&|\\]/\\&/g')
        sed -i "s|^DEMO_PASSWORD=.*|DEMO_PASSWORD=${CLAVE_ESC}|" .env
    fi
    if [[ "$DB_LOCAL" == "--db-local" ]]; then
        DBPASS=$(.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(18))")
        sudo mariadb -e "CREATE DATABASE IF NOT EXISTS sgr CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
            CREATE USER IF NOT EXISTS 'sgr_app'@'localhost' IDENTIFIED BY '${DBPASS}';
            GRANT ALL PRIVILEGES ON sgr.* TO 'sgr_app'@'localhost'; FLUSH PRIVILEGES;"
        sed -i "s|^DB_HOST=.*|DB_HOST=127.0.0.1|; s|^DB_USER=.*|DB_USER=sgr_app|; s|^DB_PASSWORD=.*|DB_PASSWORD=${DBPASS}|" .env
    else
        echo "!! Complete DB_HOST (endpoint RDS), DB_USER y DB_PASSWORD en $APP_DIR/.env y vuelva a ejecutar."
        exit 1
    fi
    chmod 600 .env
fi

echo "==> Migraciones, archivos estáticos y datos"
.venv/bin/python manage.py check --deploy || true
.venv/bin/python manage.py migrate --noinput
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py seed_data --volumen
mkdir -p media && sudo chown -R "$APP_USER:$WEB_GROUP" media && chmod 775 media

echo "==> gunicorn (systemd) y nginx"
# El servicio se escribe con el usuario de la instancia y el grupo de nginx (así nginx puede usar el socket).
sed -e "s/^User=.*/User=$APP_USER/" -e "s/^Group=.*/Group=$WEB_GROUP/" deploy/gunicorn-sgr.service \
    | sudo tee /etc/systemd/system/gunicorn-sgr.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn-sgr
sudo systemctl restart gunicorn-sgr
# nginx.conf trae su propio sitio de ejemplo en el puerto 80: se le quita default_server para que
# el del SGR atienda las peticiones por IP.
sudo sed -i 's/\(listen[^;]*\) default_server/\1/' /etc/nginx/nginx.conf
if [[ -d /etc/nginx/sites-available ]]; then
    sudo cp deploy/nginx-sgr.conf /etc/nginx/sites-available/sgr
    sudo ln -sf /etc/nginx/sites-available/sgr /etc/nginx/sites-enabled/sgr
    sudo rm -f /etc/nginx/sites-enabled/default
else
    sudo cp deploy/nginx-sgr.conf /etc/nginx/conf.d/sgr.conf
fi
sudo systemctl enable nginx
sudo nginx -t
sudo systemctl restart nginx

echo "==> Listo: http://$(curl -s --max-time 3 http://checkip.amazonaws.com || echo '<IP-publica>')/"
