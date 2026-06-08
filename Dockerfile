FROM python:3.11-slim

WORKDIR /app/pgadmin4

# Install system dependencies required for building python packages like psycopg
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install dependencies, including gunicorn for production server and redis if task queue needs it
RUN pip install --no-cache-dir -r requirements.txt gunicorn redis celery

# Copy application source
COPY . .

# Set up the entrypoint
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Expose pgAdmin default port
EXPOSE 5050

ENTRYPOINT ["docker-entrypoint.sh"]
