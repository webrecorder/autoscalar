#!/bin/bash

if [ -d /data/warcs ]; then
  tar cvfz /collections.warc.gz /data/warcs/collections/
fi

mysqladmin --user=root --password=password -h127.0.0.1 --protocol=tcp shutdown

echo "Ready for commit"

