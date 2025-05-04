#!/bin/bash

## debug flask server for dev.
# ** listens on all interfaces, dont use this in prod **
PORT=${1:-9999}

# activate python virtual env
. .venv/bin/activate

unset PYTHONPATH # debugger is not available when this is set.
export WERKZEUG_DEBUG_PIN=off

KEY=secrets/self-key.pem
CERT=secrets/self-cert.pem

if [[ ! -f $KEY ]] || [[ ! -f $CERT ]]; then
  echo Creating SSL key...
  openssl req -x509 -newkey rsa:4096 -keyout $KEY -out $CERT -days 365 -nodes -subj "/C=US/ST=State/L=City/O=Organization/OU=Unit/CN=example.com"
fi

flask --app backend/app --debug run -h 0.0.0.0 -p $PORT --cert=$CERT --key=$KEY
