data "azurerm_client_config" "deployer" {}

resource "azurerm_storage_account" "staticweb" {
  name                      = local.staticweb_storage_name
  resource_group_name       = var.resource_group_name
  location                  = var.location
  account_kind              = "StorageV2"
  account_tier              = "Standard"
  account_replication_type  = "LRS"
  enable_https_traffic_only = true
  allow_blob_public_access  = false

  tags = {
    tre_id = var.tre_id
  }

  static_website {
    index_document     = "index.html"
    error_404_document = "404.html"
  }

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_storage_blob" "staticweb" {
  name                   = "index.html"
  storage_account_name   = azurerm_storage_account.staticweb.name
  storage_container_name = "$web"
  type                   = "Block"
  content_type           = "text/html"
  source_content         = local.staticweb_index_file_content

  lifecycle { ignore_changes = [tags] }
}

resource "azurerm_storage_account_network_rules" "staticweb" {
  resource_group_name  = var.resource_group_name
  storage_account_name = azurerm_storage_account.staticweb.name

  bypass         = ["AzureServices"]
  default_action = "Deny"

  depends_on = [
    azurerm_storage_blob.staticweb
  ]
}

# Assign the "Storage Blob Data Contributor" role needed for uploading certificates to the storage account
resource "azurerm_role_assignment" "stgwriter" {
  scope                = azurerm_storage_account.staticweb.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = data.azurerm_client_config.deployer.object_id
}

resource "azurerm_private_endpoint" "webpe" {
  name                = "pe-web-${local.staticweb_storage_name}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.shared_subnet

  lifecycle { ignore_changes = [tags] }

  private_dns_zone_group {
    name                 = "private-dns-zone-group-web"
    private_dns_zone_ids = [var.static_web_dns_zone_id]
  }

  private_service_connection {
    name                           = "psc-web--${local.staticweb_storage_name}"
    private_connection_resource_id = azurerm_storage_account.staticweb.id
    is_manual_connection           = false
    subresource_names              = ["web"]
  }
}
