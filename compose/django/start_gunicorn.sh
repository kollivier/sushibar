#!/bin/sh
echo "Migrating DB >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
python /app/manage.py migrate --noinput

echo "Collecting static files >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
python /app/manage.py collectstatic --noinput

# Optional for dev:
# echo "Loading admin user fixture >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>"
# python /app/manage.py loaddata /app/sushibar/users/fixtures/admin_user.json

/usr/local/bin/gunicorn config.wsgi -w 4 -b 0.0.0.0:5000 --chdir=/app
