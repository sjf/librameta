#!/bin/bash

set -eux
# Start containers
docker compose up --quiet-pull -d elasticsearch db

# Reset dumps.
rm -rvf dumps

# Copy test dataset
mkdir -p dumps/fiction
mkdir -p dumps/libmeta
mkdir -p dumps/libmeta_compact

for db in fiction libmeta libmeta_compact; do
  mkdir -p dumps/${db}/
  cp -v scripts/${db}.rar dumps/${db}/
done

# Do the imports
scripts/wait_for_containers.sh 2 60 ${COMPOSE_PROJECT_PREFIX:-}elasticsearch ${COMPOSE_PROJECT_PREFIX:-}db
import/import.py -d -c -m MYSQL_IMPORT_AND_ES_IMPORT
import/import.py -d -m ES_COMPARE_AND_IMPORT

