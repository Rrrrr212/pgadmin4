#!/usr/bin/env bash
set -e

PUID=${PUID:-5050}
PGID=${PGID:-0}

if [ "$(id -u)" = "0" ]; then
    if ! getent group "$PGID" > /dev/null 2>&1; then
        groupadd -g "$PGID" pggroup
    fi
    usermod -o -u "$PUID" -g "$PGID" pgadmin 2>/dev/null || true
    for dir in /run/pgadmin /var/lib/pgadmin /var/log/pgadmin; do
        if [ -d "$dir" ]; then
            chown -R "$PUID:$PGID" "$dir"
        fi
    done
    if [ -e /pgadmin4/config_distro.py ]; then
        chown "$PUID:$PGID" /pgadmin4/config_distro.py
    fi
    GOSU="gosu $PUID:$PGID"
else
    GOSU=""
fi

export CONFIG_DISTRO_FILE_PATH="${PGADMIN_CUSTOM_CONFIG_DISTRO_FILE:-/pgadmin4/config_distro.py}"

if [ ! -e "${CONFIG_DISTRO_FILE_PATH}" ] || [ "$(wc -m "${CONFIG_DISTRO_FILE_PATH}" 2>/dev/null | awk '{ print $1 }')" = "0" ]; then
    cat << EOF > "${CONFIG_DISTRO_FILE_PATH}"
CA_FILE = '/etc/ssl/certs/ca-certificates.crt'
LOG_FILE = '/var/log/pgadmin/pgadmin4.log'
HELP_PATH = '../../docs'
DEFAULT_BINARY_PATHS = {
    'pg': '/usr/bin',
    'pg-18': '/usr/bin',
    'pg-17': '/usr/bin',
    'pg-16': '/usr/bin',
    'pg-15': '/usr/bin',
    'pg-14': '/usr/bin',
    'pg-13': '/usr/bin'
}
EOF

    for var in $(env | grep "^PGADMIN_CONFIG_" | cut -d "=" -f 1); do
        val=$(eval "echo \"\$$var\"")
        case "$(echo "$val" | tr '[:upper:]' '[:lower:]')" in
            true)  val="True" ;;
            false) val="False" ;;
        esac
        echo "${var#PGADMIN_CONFIG_} = $val" >> "${CONFIG_DISTRO_FILE_PATH}"
    done

    if [ "$(id -u)" = "0" ] && [ "${CONFIG_DISTRO_FILE_PATH}" != "/pgadmin4/config_distro.py" ]; then
        chown "$PUID:$PGID" "${CONFIG_DISTRO_FILE_PATH}"
    fi
fi

external_config_db_exists="False"
if [ -n "${PGADMIN_CONFIG_CONFIG_DATABASE_URI}" ]; then
    external_config_db_exists=$(cd /pgadmin4/pgadmin/utils && $GOSU python3 -c "from check_external_config_db import check_external_config_db; val = check_external_config_db(\"${PGADMIN_CONFIG_CONFIG_DATABASE_URI}\"); print(val)" 2>/dev/null || echo "False")
fi

if [ ! -f /var/lib/pgadmin/pgadmin4.db ] && [ "${external_config_db_exists}" = "False" ]; then
    if [ -z "${PGADMIN_DEFAULT_EMAIL}" ] || [ -z "${PGADMIN_DEFAULT_PASSWORD}" ]; then
        echo 'ERROR: PGADMIN_DEFAULT_EMAIL and PGADMIN_DEFAULT_PASSWORD must be set on first run.'
        exit 1
    fi

    export PGADMIN_SETUP_EMAIL="${PGADMIN_DEFAULT_EMAIL}"
    export PGADMIN_SETUP_PASSWORD="${PGADMIN_DEFAULT_PASSWORD}"

    cd /pgadmin4
    $GOSU python3 run_pgadmin.py

    if [ -f "${PGADMIN_SERVER_JSON_FILE:-/pgadmin4/servers.json}" ]; then
        $GOSU python3 /pgadmin4/setup.py load-servers "${PGADMIN_SERVER_JSON_FILE}" --user "${PGADMIN_DEFAULT_EMAIL}"
    fi
fi

TIMEOUT=$(cd /pgadmin4 && $GOSU python3 -c 'import config; print(config.SESSION_EXPIRATION_TIME * 60 * 60 * 24)' 2>/dev/null || echo 28800)

BIND_ADDRESS="${PGADMIN_LISTEN_ADDRESS:-0.0.0.0}:${PGADMIN_LISTEN_PORT:-5050}"

exec $GOSU python3 /usr/local/bin/gunicorn \
    --limit-request-line 8190 \
    --timeout "${TIMEOUT}" \
    --bind "${BIND_ADDRESS}" \
    -w 1 \
    --threads "${GUNICORN_THREADS:-25}" \
    --access-logfile "-" \
    -c gunicorn_config.py \
    run_pgadmin:app
