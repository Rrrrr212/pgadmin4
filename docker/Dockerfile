FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
        gcc \
        libldap2-dev \
        libsasl2-dev \
        postgresql-client \
        gosu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /pgadmin4
ENV PYTHONPATH=/pgadmin4

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir \
        gunicorn==23.0.0 \
        psycopg[c]==3.2.13 \
        redis==5.* \
        celery==5.*

COPY web/ /pgadmin4/
COPY pkg/docker/run_pgadmin.py /pgadmin4/
COPY pkg/docker/gunicorn_config.py /pgadmin4/
COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN useradd -r -u 5050 -g root -s /sbin/nologin pgadmin \
    && mkdir -p /run/pgadmin /var/lib/pgadmin /var/log/pgadmin \
    && chown pgadmin:root /run/pgadmin /var/lib/pgadmin /var/log/pgadmin \
    && chmod g=u /run/pgadmin /var/lib/pgadmin /var/log/pgadmin \
    && touch /pgadmin4/config_distro.py \
    && chown pgadmin:root /pgadmin4/config_distro.py \
    && chmod g=u /pgadmin4/config_distro.py \
    && chmod +x /usr/local/bin/entrypoint.sh

VOLUME ["/var/lib/pgadmin"]

EXPOSE 5050

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
