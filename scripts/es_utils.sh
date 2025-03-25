#!/bin/bash
INDEX1=libmeta1
INDEX2=libmeta2
ALIAS=libmeta_alias

ESPASS=$(cat secrets/elastic-password.txt.orig)
ELASTIC_HOST='http://localhost:9200'

export bold=$(tput bold)
export normal=$(tput sgr0)

function jcurl(){
  VERB=$1; shift
  URLPATH=$1; shift
  ARGS=
  if [[ $VERB == 'HEAD' ]]; then
    # only headers, dont try to read response body. Return error code if not found.
    echo curl -If --retry 0 -sS -u elastic:$ESPASS -X $VERB ${ELASTIC_HOST}${URLPATH} >&2
         curl -If --retry 0 -sS -u elastic:$ESPASS -X $VERB ${ELASTIC_HOST}${URLPATH} > /dev/null
    return
  fi
  echo curl --retry 0 -sS -H 'Content-Type: application/json' -u elastic:$ESPASS -X $VERB ${ELASTIC_HOST}${URLPATH} $ARGS $@ >&2
       curl --retry 0 -sS -H 'Content-Type: application/json' -u elastic:$ESPASS -X $VERB ${ELASTIC_HOST}${URLPATH} $ARGS $@
  echo
}
