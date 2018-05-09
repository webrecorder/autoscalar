#!/bin/bash

/tmp/restart-run.sh docker-entrypoint.sh mysqld --verbose &

if [ -f /collections.warc.gz ]; then
    tar xvfz /collections.warc.gz -C /
fi

apache2-foreground

