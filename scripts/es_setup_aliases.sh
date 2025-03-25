#!/bin/bash
set -ue

. $(dirname $0)/es_utils.sh

SWAP="
{
  \"actions\": [ {
      \"remove\": {
        \"index\": \"$INDEX2\",
        \"alias\": \"$ALIAS\"
      }
    },
    {
      \"add\": {
        \"index\": \"$INDEX1\",
        \"alias\": \"$ALIAS\"
      }
    }
  ]
}"
echo "${bold}Setting up aliases: add $INDEX1, remove $INDEX2 to $ALIAS ${normal}"
echo $SWAP | jcurl POST "/_aliases" -d @-


