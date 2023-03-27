#!/bin/bash
set -o errexit
set -o pipefail
set -o nounset

# This script is designed to be `source`d to create reusable helper functions

# This script
function construct_tre_url()
{
  tre_id=$1
  location=$2
  azure_environment=$3

  declare -A cloudapp_endpoint_suffixes=( ["AzureCloud"]="cloudapp.azure.com" ["AzureUSGovernment"]="cloudapp.usgovcloudapi.net" )
  domain=${cloudapp_endpoint_suffixes[${azure_environment}]}

  echo https://"${tre_id}"."${location}"."${domain}"
}
