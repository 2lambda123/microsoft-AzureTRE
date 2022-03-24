#!/bin/bash
set -e

response=$(curl -k "https://${TRE_ID}.${LOCATION}.cloudapp.azure.com/api/health")

not_ok_count=$(echo "${response}"  | jq -r '[.services | .[] | select(.status!="OK")] | length')

if [[ "$not_ok_count" == "0" ]]; then
  echo "API Healthy"
else
  echo "API _not_ healthy. Unhealthy services:"
  echo "${response}"  | jq -r '[.services | .[] | select(.status!="OK")]'
  exit 1
fi
