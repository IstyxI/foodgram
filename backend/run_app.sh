#!/bin/sh
set -e
cd foodgram
python manage.py collectstatic --no-input
python manage.py migrate
exec "$@"