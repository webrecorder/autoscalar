#!/bin/bash

cd /data/warcs/

if [ ! -d /data/warcs/collections ]; then
  wb-manager init store
fi

cp /app/templates/banner.html /data/warcs/templates/
cp -r /app/static/* /data/warcs/static/

#python -u /app/captureworker.py &

#python -u /app/dynproxyapp.py

uwsgi /app/capture.ini &

uwsgi /app/uwsgi.ini

