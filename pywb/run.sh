#!/bin/bash

cd /data/warcs/

if [ ! -d /data/warcs/collections ]; then
  # new capture
  wb-manager init store
  
  cp /app/templates/banner.html /data/warcs/templates/
  cp -r /app/static/* /data/warcs/static/

else
  #mkdir -p /data/warcs/collections/store
  #mkdir -p /data/warcs/collections/store/archive
  #mkdir -p /data/warcs/collections/store/indexes

  mkdir -p /data/warcs/static/
  cp -r /app/static/default_banner.* /data/warcs/static/

  # replay, wait for volume to be filled with data
  while [ ! -d /data/warcs/collections/store/indexes ]
  do
    echo "Wait for volume to contain data"
    sleep 2
  done

fi

#python -u /app/captureworker.py &

#python -u /app/dynproxyapp.py

uwsgi /app/capture.ini &

uwsgi /app/uwsgi.ini

