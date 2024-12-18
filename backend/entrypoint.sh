#!/bin/sh
set -e
cd foodgram
while ! nc -z db 5432;
    do sleep .5;
    echo "wait database";
done;
    echo "connected to the database";

python manage.py collectstatic --no-input
python manage.py migrate
exec "$@"