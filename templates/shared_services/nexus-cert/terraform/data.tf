data "azurerm_resource_group" "rg" {
  name = "rg-${var.tre_id}"
}

data "azurerm_key_vault" "key_vault" {
  name                = "kv-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.rg.name
}

data "azurerm_subnet" "app_gw_subnet" {
  name                 = "AppGwSubnet"
  virtual_network_name = "vnet-${var.tre_id}"
  resource_group_name  = data.azurerm_resource_group.rg.name
}

data "azurerm_public_ip" "appgwpip_data" {
  depends_on          = [azurerm_application_gateway.agw]
  name                = "pip-nexus-${var.tre_id}"
  resource_group_name = data.azurerm_resource_group.rg.name
}
