#!/bin/bash
set -ue
. $(dirname $0)/es_utils.sh

echo "${bold}Activating basic license${normal}"
jcurl POST "/_license/start_basic?acknowledge=true"

echo "${bold}Disable automatic index creation${normal}"
ACI='{
  "persistent": {
    "action.auto_create_index": "-libmeta*"
  }
}'
echo $ACI | jcurl PUT "/_cluster/settings" -d @-

# If this is failing with "no handler found for uri [/_security... security is disabled in the ES settings.
# The REST API uses the base64 encoded api key, not the 'api_key' in the response.
# The analyze api stupidly needs the manage permission.
echo "${bold}Creating api key for backend${normal}"
KEY='
{
  "name": "read_only_key",
  "role_descriptors": {
    "read_only_role": {
      "cluster": [],
      "index": [
        {
          "names": ["*"],
          "privileges": ["read", "manage"]
        }
      ]
    }
  }
}'
echo $KEY | jcurl POST "/_security/api_key" -d @- | jq -r .encoded > secrets/elastic-api-key.txt

echo "${bold}Creating admin api key with all privileges${normal}"
ADMIN_KEY='
{
  "name": "all_access_key",
  "role_descriptors": {
    "all_access_role": {
      "cluster": ["all"],
      "index": [
        {
          "names": ["*"],
          "privileges": ["all"]
        }
      ]
    }
  }
}'
echo $ADMIN_KEY | jcurl POST "/_security/api_key" -d @- | jq -r .encoded > secrets/elastic-admin-api-key.txt

echo "${bold}Creating service account token for kibana${normal}"
jcurl POST "/_security/service/elastic/kibana/credential/token" |\
  jq -r  .token.value > secrets/elastic-service-account-token.txt

TOKEN=$(cat secrets/elastic-service-account-token.txt)
sed -i "s/^ELASTICSEARCH_SERVICEACCOUNTTOKEN=.*/ELASTICSEARCH_SERVICEACCOUNTTOKEN=$TOKEN/" .env

