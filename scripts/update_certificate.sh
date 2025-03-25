#!/bin/bash
set -eu

QUIET=
if [[ ${1:-} == "-s" ]]; then
  QUIET="yes"
fi

URL=https://api.porkbun.com/api/json/v3/ssl/retrieve/libmeta.net

cat secrets/porkbun.json | curl -s -X POST $URL -H 'Content-Type: application/json' -d @- > /tmp/out.json
jq -r .certificatechain /tmp/out.json  > /tmp/domain.cert.pem

if cmp /tmp/domain.cert.pem secrets/ssl/domain.cert.pem; then
  if [[ $QUIET != "yes" ]]; then
    echo domain.cert.pem has not changed.
  fi
  rm /tmp/out.json
  rm /tmp/domain.cert.pem
  exit 0
fi

echo Updating certificate...
echo

CERT_FILE=/tmp/domain.cert.pem
openssl x509 -in "$CERT_FILE" -text -noout
not_before=$(openssl x509 -in "$CERT_FILE" -noout -startdate | cut -d= -f2)
not_after=$(openssl x509 -in "$CERT_FILE" -noout -enddate | cut -d= -f2)
not_before_epoch=$(date -d "$not_before" +%s)
not_after_epoch=$(date -d "$not_after" +%s)
current_epoch=$(date +%s)
if [[ $current_epoch -ge $not_before_epoch && $current_epoch -le $not_after_epoch ]]; then
  echo "The current date is within the certificate's validity period."
else
  echo " ** The current date is outside the certificate's validity period. **"
  exit 1
fi
set -x
mv /tmp/domain.cert.pem secrets/ssl/
jq -r .publickey /tmp/out.json > secrets/ssl/publickey.pem
jq -r .privatekey /tmp/out.json > secrets/ssl/private.key.pem
# verify the expirate date
rm /tmp/out.json

docker exec -u root -it frontend nginx -s reload




