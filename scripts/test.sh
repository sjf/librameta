#!/bin/bash
set -eux

if [ -n "${TEST:-}" ]; then
  # Use a test docker compose project, instead of the default.
  # This is to be able to run the tests in a separate environment
  # while having a dev docker instance on the same machine.
  # Specifically, it is so the contents of the elasticsearch index and MySQL DB
  # do not get reset.
  export COMPOSE_FILE=compose.yaml:compose.test.yaml
  export COMPOSE_PROJECT_NAME=test
  export COMPOSE_PROJECT_PREFIX=test_
else
  unset COMPOSE_FILE
  unset COMPOSE_PROJECT_NAME
  COMPOSE_PROJECT_PREFIX=''
fi
export COMPOSE_FILE
export COMPOSE_PROJECT_NAME
export COMPOSE_PROJECT_PREFIX

if [[ "${RESET:-no}" == "yes" ]]; then
  scripts/reset_environment.sh
  scripts/setup.sh # This does nothing if environment is already set up.
  scripts/es_setup.sh # Set up elasticsearch api keys, etc and indexes. Idempotent.
  import/indexes.py list # List elasticsearch indexes and their sizes.
  docker compose up --quiet-pull -d frontend backend db
else
  # Just down the containers and rebuild them.
  # not elasticearch bc it takes too long to start and the container does not change.
  docker compose up --build --quiet-pull --no-deps -d frontend backend
fi

scripts/import.sh # only needs on elasticsearch and db containers.
import/indexes.py list

./scripts/wait_for_containers.sh 2 60 ${COMPOSE_PROJECT_PREFIX}frontend ${COMPOSE_PROJECT_PREFIX}backend

BACKEND=https://localhost TEST_DOWNLOAD=False VERIFY_SSL=False PYTHONWARNINGS="ignore:Unverified HTTPS request" pytest -vvvv
KEEP_TESTS=1 ./scripts/logs_anal.sh
./scripts/verify_logs.sh
echo ------- TESTS PASSED -------
