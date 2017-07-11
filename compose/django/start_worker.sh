#!/bin/bash
set -e

NAME="asgi_worker"               # Name of the application
DJANGO_DIR=/app                  # Django project directory

echo "Starting $NAME as `whoami`"

cd $DJANGO_DIR

# Start ASGI worker
exec ./manage.py runworker
