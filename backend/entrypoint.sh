#!/bin/sh
set -e
export PYTHONPATH=/app:$PYTHONPATH
cd /app/backend
python manage.py makemigrations users
python manage.py makemigrations api
python manage.py migrate
python manage.py collectstatic --no-input
python manage.py load_ingredients
python manage.py load_tags
exec "$@"