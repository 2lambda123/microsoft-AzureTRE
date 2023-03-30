terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "=3.40.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "=1.1.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "=1.5.0"
    }
    dns = {
      source  = "hashicorp/dns"
      version = "=3.2.3"
    }
  }

  backend "azurerm" {}
}

provider "azurerm" {
  features {
    key_vault {
      # Don't purge on destroy (this would fail due to purge protection being enabled on keyvault)
      purge_soft_delete_on_destroy               = false
      purge_soft_deleted_secrets_on_destroy      = false
      purge_soft_deleted_certificates_on_destroy = false
      purge_soft_deleted_keys_on_destroy         = false
      # When recreating an environment, recover any previously soft deleted secrets - set to true by default
      recover_soft_deleted_key_vaults   = true
      recover_soft_deleted_secrets      = true
      recover_soft_deleted_certificates = true
      recover_soft_deleted_keys         = true
    }
  }
}

provider "azapi" {
}

provider "databricks" {
  host                        = azurerm_databricks_workspace.databricks.workspace_url
  azure_workspace_resource_id = azurerm_databricks_workspace.databricks.id

  azure_use_msi = true
}

module "azure_region" {
  source  = "claranet/regions/azurerm"
  version = "=6.1.0"

  azure_region = data.azurerm_resource_group.ws.location
}

provider "dns" {
}

module "terraform_azurerm_environment_configuration" {
  source          = "git::https://github.com/microsoft/terraform-azurerm-environment-configuration.git?ref=fa7a3809a24f97d43737eaf72ed13eaef70fb369"
  arm_environment = var.arm_environment
}
