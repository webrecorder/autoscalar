#!/bin/bash

cd /data/warcs/

if [ ! -d /data/warcs/collections ]; then
  wb-manager init store
fi

python -u /app/dynproxyapp.py

