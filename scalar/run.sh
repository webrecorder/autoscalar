#!/bin/bash

#/tmp/init.sh &
docker-entrypoint.sh mysqld &

apache2-foreground

