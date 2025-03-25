#!/bin/bash
set -eu

mkdir -p secrets

[ ! -f secrets/db-password.txt ]      && uuidgen | tr -d '-' | head -c 12 > secrets/db-password.txt
[ ! -f secrets/db-user-password.txt ] && uuidgen | tr -d '-' | head -c 12 > secrets/db-user-password.txt
[ ! -f secrets/elastic-password.txt ] && uuidgen | tr -d '-' | head -c 12 > secrets/elastic-password.txt
[ ! -f secrets/flask-secret-key.txt ] && uuidgen | tr -d '-' | head -c 12 > secrets/flask-secret-key.txt

# elasticsearch refuses to start if permissions are not correct.
chmod 600 secrets/elastic-password.txt
# This is required because ES requires a specific owner and permissions
# that make the file unreadable to the host when running in github actions.
cp secrets/elastic-password.txt secrets/elastic-password.txt.orig

if [ ! -f secrets/mb-password.txt ]; then
  PASS=$(uuidgen | tr -d '-' | head -c 12 | tee secrets/mb-password.txt)
  htpasswd -cb secrets/htpasswd mb $PASS
fi

if [ ! -f secrets/files-password.txt ]; then
  PASS=$(uuidgen | tr -d '-' | head -c 12 | tee secrets/files-password.txt)
  htpasswd -cb secrets/files_htpasswd mb $PASS
fi

chmod 644 secrets/files_htpasswd secrets/htpasswd

# file has to exist for docker secret binding to work.
touch secrets/elastic-api-key.txt

[ ! -f scripts/config.ini ] && cp scripts/config.ini secrets/

if [ ! -f .env ]; then
  # Env var is used by kibana and has to be set for docker compose to work.
  echo ELASTICSEARCH_SERVICEACCOUNTTOKEN=NO_VALUE > .env
fi

SSL=secrets/ssl
if [ ! -d $SSL ]; then
  set -x
  mkdir $SSL
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout $SSL/private.key.pem \
    -out $SSL/domain.cert.pem -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=localhost"
fi

if [ ! -d .venv ]; then
  python -m venv .venv
  . .venv/bin/activate
  pip install -qr requirements.txt
  pip install -e mbutils
fi
