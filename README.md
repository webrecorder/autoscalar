# Webrecorder Auto Archiver for Scalar Prototype

This repo represents the experimental prototype for automatically archiving and preserving Scalar website and all external links.

The system combines three key concepts:
- automated server software preservation (via a Docker image)
- automated high-fidelity browser based web archiving
- browser preservation (via Docker image, oldwebtoday system)

A demo of this prototype is available at: https://scalar.webrecorder.net/

Please note that this is still a prototype and may not work for all Scalar sites.

More high-level info about how this system works is available at: https://docs.google.com/presentation/d/1_AoCavSoZRFZp6KNpRcYfhJe9am4XCJIWN26mP4Haro/edit?usp=sharing

## Installation

1. First build the instance Docker images via: `docker-compose -f ./docker-compose-instance.yml build`

2. Start the standard Docker compose with `docker-compose build; docker-compose up -d`

Note: The prototype does not yet clean up all the containers created, eg. if a user doesn't click "Stop".
To clean up containers and volumes, run `./rm-containers.sh`. This will stop all running Scalar instance containers.

The default setup does not require a password for creating new archives. To setup a password, set the `AUTH_CODE` env var in `docker-compose.yml`
