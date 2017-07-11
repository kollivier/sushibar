#!/bin/bash
set -e

NAME="sushibar_daphne"                               # Name of the application
DJANGO_DIR=/app                                      # Django project directory
DAPHNE_BIN=/usr/local/bin/daphne
DAPHNE_PORT=6000
DJANGO_ASGI_MODULE=config.asgi                       # ASGI module name
# USER=django                                        # the user to run as
# GROUP=webapps                                      # the group to run as

echo "Starting $NAME as `whoami`"

cd $DJANGO_DIR

# Start Daphne ASGI server
exec $DAPHNE_BIN -b 0.0.0.0 -p $DAPHNE_PORT  ${DJANGO_ASGI_MODULE}:channel_layer
