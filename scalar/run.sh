#!/bin/bash

docker-entrypoint.sh mysqld &

if [ -f /collections.warc.gz ]; then
    tar xvfz /collections.warc.gz -C /
fi

apache2-foreground

