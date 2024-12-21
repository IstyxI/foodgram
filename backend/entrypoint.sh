#!/bin/sh
set -e
cd /app/backend
python manage.py collectstatic --no-input
python manage.py migrate
exec "$@"