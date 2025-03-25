#!/bin/bash
if [ -t 0 ]; then
  echo Resetting the environment.
  echo '** Enter to continer, Ctrl-C to cancel. Waiting 20 seconds... **'
  read -t 20 _
fi
# Reset environment.
rm -rf .venv/ 2>/dev/null
rm -vrf secrets/ 2>/dev/null
rm -vf .env 2>/dev/null
rm -vf admin/*.txt 2>/dev/null
rm -vf admin/downloads.html 2>/dev/null

# Env var is used by kibana and has to be set for docker compose to work.
echo ELASTICSEARCH_SERVICEACCOUNTTOKEN=NO_VALUE > .env

# Reset docker containers and volumes.
docker compose --profile default --profile db --profile kibana down -v

rm -vf logs/*.log  2>/dev/null
rm -vf logs/nginx/*.log  2>/dev/null
rm -vf logs/mysql/*.log  2>/dev/null

