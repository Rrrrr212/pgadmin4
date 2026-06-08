#!/bin/bash
set -e

mkdir -p /var/lib/pgadmin /var/log/pgadmin
mkdir -p /var/lib/pgadmin/sessions /var/lib/pgadmin/storage

cat << 'EOF' > /app/pgadmin4/web/config_local.py
import os

SERVER_MODE = True
DATA_DIR = '/var/lib/pgadmin'
LOG_FILE = '/var/log/pgadmin/pgadmin4.log'
SQLITE_PATH = '/var/lib/pgadmin/pgadmin4.db'
SESSION_DB_PATH = '/var/lib/pgadmin/sessions'
STORAGE_DIR = '/var/lib/pgadmin/storage'
AZURE_CREDENTIAL_CACHE_DIR = '/var/lib/pgadmin/azurecredentialcache'
KERBEROS_CCACHE_DIR = '/var/lib/pgadmin/kerberoscache'

for key, value in os.environ.items():
    if key.startswith('PGADMIN_CONFIG_'):
        config_key = key[15:]
        if value.lower() == 'true':
            globals()[config_key] = True
        elif value.lower() == 'false':
            globals()[config_key] = False
        else:
            try:
                globals()[config_key] = int(value)
            except ValueError:
                globals()[config_key] = value
EOF

export PGADMIN_SETUP_EMAIL=${PGADMIN_DEFAULT_EMAIL:-admin@admin.com}
export PGADMIN_SETUP_PASSWORD=${PGADMIN_DEFAULT_PASSWORD:-admin}

echo "Initializing configuration database..."
python /app/pgadmin4/web/setup.py setup-db

echo "Starting pgAdmin 4..."
exec gunicorn --bind 0.0.0.0:5050 -w 1 --threads 25 --chdir /app/pgadmin4/web pgAdmin4:app