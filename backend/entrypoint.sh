#!/bin/sh
set -e
export PYTHONPATH=/app:$PYTHONPATH
cd /app/backend
python manage.py collectstatic --no-input
python manage.py migrate
exec "$@"