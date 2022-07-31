#!/bin/bash

set -o errexit
set -o pipefail
set -o nounset
# set -o xtrace

# This variables are loaded in for us
# shellcheck disable=SC2154
terraform init -input=false -backend=true -reconfigure -upgrade \
    -backend-config="resource_group_name=${TF_VAR_mgmt_resource_group_name}" \
    -backend-config="storage_account_name=${TF_VAR_mgmt_storage_account_name}" \
    -backend-config="container_name=${TF_VAR_terraform_state_container_name}" \
    -backend-config="key=${TRE_ID}"

echo "*** Migrating TF Resources ***"
# 1. Check we have a root_module in state
# 2. Grab the Resource ID
# 3. Delete the old resource from state
# 4. Import the new resource type in using the existing Azure Resource ID

terraform_show_json=$(terraform show -json)

# azurerm_app_service_plan -> azurerm_service_plan
core_app_service_plan_id=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.resources != null) | .values.root_module.resources[] | select(.address=="azurerm_app_service_plan.core") | .values.id')
if [ -n "${core_app_service_plan_id}" ]; then
  echo "Migrating ${core_app_service_plan_id}"
  terraform state rm azurerm_app_service_plan.core
  if [[ $(az resource list --query "[?id=='${core_app_service_plan_id}'] | length(@)") == 0 ]];
  then
    echo "The resource doesn't exist on Azure. Skipping importing it back to state."
  else
    terraform import azurerm_service_plan.core "${core_app_service_plan_id}"
  fi
fi

# azurerm_app_service -> azurerm_linux_web_app
api_app_service_id=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.resources != null) | .values.root_module.resources[] | select(.address=="azurerm_app_service.api") | .values.id')
if [ -n "${api_app_service_id}" ]; then
  echo "Migrating ${api_app_service_id}"
  terraform state rm azurerm_app_service.api
  if [[ $(az resource list --query "[?id=='${api_app_service_id}'] | length(@)") == 0 ]];
  then
    echo "The resource doesn't exist on Azure. Skipping importing it back to state."
  else
    terraform import azurerm_linux_web_app.api "${api_app_service_id}"
  fi
fi

# app insights via -> native tf resource
app_insights_via_arm=$(echo "${terraform_show_json}" \
  | jq -r 'select(.values.root_module.child_modules != null) .values.root_module.child_modules[] | select (.address=="module.azure_monitor") | .resources[] | select(.address=="module.azure_monitor.azurerm_resource_group_template_deployment.app_insights_core") | .values.id')
if [ -n "${app_insights_via_arm}" ]; then
  echo "Migrating ${app_insights_via_arm}"

  PLAN_FILE="tfplan$$"
  TS=$(date +"%s")
  LOG_FILE="${TS}-tre-core-migrate.log"

  # This variables are loaded in for us
  # shellcheck disable=SC2154
  ../../../devops/scripts/terraform_wrapper.sh \
    -g "${TF_VAR_mgmt_resource_group_name}" \
    -s "${TF_VAR_mgmt_storage_account_name}" \
    -n "${TF_VAR_terraform_state_container_name}" \
    -k "${TRE_ID}" \
    -l "${LOG_FILE}" \
    -c "terraform plan -target module.azure_monitor.azurerm_resource_group_template_deployment.app_insights_core -target module.azure_monitor.azurerm_resource_group_template_deployment.ampls_core -out ${PLAN_FILE} && \
    terraform apply -input=false -auto-approve ${PLAN_FILE}"
fi

echo "Migration is done."
