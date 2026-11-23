#!/bin/sh
set -e

# Set defaults for host and port if not provided
POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
REDIS_HOST=${REDIS_HOST:-cache}
REDIS_PORT=${REDIS_PORT:-6379}

# Wait for the database to be ready
echo "Waiting for postgres at $POSTGRES_HOST:$POSTGRES_PORT..."
while ! nc -z "$POSTGRES_HOST" "$POSTGRES_PORT"; do
  sleep 0.1
done
echo "PostgreSQL started"

# Wait for the redis to be ready
echo "Waiting for redis at $REDIS_HOST:$REDIS_PORT..."
while ! nc -z "$REDIS_HOST" "$REDIS_PORT"; do
  sleep 0.1
done
echo "Redis started"

# Apply database migrations only when enabled (run via dedicated blog_migrate job in production)
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Applying database migrations..."
  python manage.py migrate --no-input
fi

# Collect static files only when enabled
if [ "${RUN_COLLECTSTATIC:-true}" = "true" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --no-input
fi

# Start multi-worker application server
if [ "${BLOG_SERVER_MODE:-wsgi}" = "asgi" ]; then
  echo "Starting ASGI Daphne server..."
  exec daphne -b 0.0.0.0 -p 8000 blog.asgi:application
fi

echo "Starting multi-worker Gunicorn server (workers=${GUNICORN_WORKERS:-3}, threads=${GUNICORN_THREADS:-2})..."
exec gunicorn blog.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --worker-class gthread \
  --timeout "${GUNICORN_TIMEOUT:-60}" \
  --graceful-timeout 30 \
  --max-requests "${GUNICORN_MAX_REQUESTS:-1000}" \
  --max-requests-jitter 100 \
  --access-logfile - \
  --error-logfile -
