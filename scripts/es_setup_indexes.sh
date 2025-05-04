#!/bin/bash
set -ue

. $(dirname $0)/es_utils.sh

DELETE=false
UPDATE=true
while getopts "dn" OPT; do
  case $OPT in
    d)
      DELETE=true
      ;;
    n)
      UPDATE=false
      ;;
    *)
      echo "Usage: $0 [-d (delete existing indexes)] [-n (don't update existing indexes)]"
      exit 1
      ;;
  esac
done

# Make dynamic mapping strict so fields cannot be added if they are not in the mapping.
# Don't index fields that are display only. Don't have doc values for fields that are not
# sorted or aggregated (i.e. none of them.)
MAPPINGS=elasticsearch/mappings.json
SETTINGS=elasticsearch/settings.json

CREATE=$(mktemp /tmp/create.json.XXXXXX)
UPDATE_SETTINGS=$(mktemp /tmp/update-settings.json.XXXXXX)

echo '{"settings": ' >> $CREATE
cat $SETTINGS >> $CREATE
echo -n ', "mappings": ' >> $CREATE
cat $MAPPINGS >> $CREATE
echo '}' >> $CREATE

# number of shards cannot be set in the update even if the value is not changing.
cat $SETTINGS | sed '/number_of_shards/d' > $UPDATE_SETTINGS

for INDEX in $INDEX1 $INDEX2; do
  if [[ $DELETE == true ]]; then
    echo "${bold}Continue to delete $INDEX, Ctrl-C to stop.${normal}"
    read -t 10
    echo "${bold}Deleting index $INDEX${normal}"
    jcurl DELETE "/$INDEX" || true
  fi

  if ! jcurl HEAD "/$INDEX/"; then
    echo "${bold}Creating index $INDEX${normal}"
    jcurl PUT "/$INDEX/" -d @${CREATE}
  else
    if [[ $UPDATE == true ]]; then
      echo "${bold}Closing $INDEX and updating.${normal}"
      jcurl POST "/$INDEX/_close"
      jcurl PUT "/$INDEX/_settings" -d @${UPDATE_SETTINGS}
      jcurl POST "/$INDEX/_open"

      jcurl PUT "/$INDEX/_mappings" -d @${MAPPINGS}
    else
      echo "${bold}Not updating existing index $INDEX${normal} (called with -n)"
    fi
  fi
  echo
done

rm $CREATE
rm $UPDATE_SETTINGS

