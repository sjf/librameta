#!/bin/bash

set -eux

docker compose up --quiet-pull -d elasticsearch

scripts/wait_for_containers.sh 2 60 ${COMPOSE_PROJECT_PREFIX:-}elasticsearch

# Set up elastic search: create index, api keys, SA token.
scripts/es_setup_roles.sh
# Create indexes, try to update existing indexes, but this is often not possible.
scripts/es_setup_indexes.sh
# Create an alias for the indexes.
scripts/es_setup_aliases.sh

