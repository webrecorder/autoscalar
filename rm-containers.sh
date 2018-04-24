#!/bin/bash

docker kill $(docker ps | grep 'dynpreserve' | cut -f 1 -d ' ')
docker kill $(docker ps | grep 'chrome' | cut -f 1 -d ' ')


