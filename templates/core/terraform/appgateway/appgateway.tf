resource "azurerm_public_ip" "appgwpip" {
  name                  = "pip-agw-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  resource_group_name   = var.resource_group_name
  location              = var.location
  allocation_method     = "Static"
  sku                   = "Standard"
  domain_name_label     = "${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
}

resource "azurerm_application_gateway" "agw" {
  name                = "agw-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  resource_group_name = var.resource_group_name
  location            = var.location

  sku {
    name     = "Standard_v2"
    tier     = "Standard_v2"
    capacity = 1
  }

  gateway_ip_configuration {
    name      = "gateway-ip-configuration"
    subnet_id = var.app_gw_subnet
  }

  frontend_port {
    name = local.frontend_port_name
    port = 80
  }

  frontend_ip_configuration {
    name                 = local.frontend_ip_configuration_name
    public_ip_address_id = azurerm_public_ip.appgwpip.id
  }
  
  backend_address_pool {
    name = local.backend_address_pool_name
  }

  backend_address_pool {
    name = local.management_api_backend_address_pool_name
    fqdns =  [var.management_api_fqdn]
  }

  backend_http_settings {
    name                  = local.http_setting_name
    cookie_based_affinity = "Disabled"
    port                  = 443
    protocol              = "Https"
    request_timeout       = 60
    pick_host_name_from_backend_address = true
    probe_name            = local.probe_name
  }

  http_listener {
    name                           = local.listener_name
    frontend_ip_configuration_name = local.frontend_ip_configuration_name
    frontend_port_name             = local.frontend_port_name
    protocol                       = "Http"
  }

  probe {
    name                                      = local.probe_name
    pick_host_name_from_backend_http_settings = true
    interval                                  = 10
    protocol                                  = "Https"
    path                                      = "/api/health"
    timeout                                   = 10
    unhealthy_threshold                       = 2
    minimum_servers                           = 0
  }

  request_routing_rule {
    name                       = local.request_routing_rule_name
    rule_type                  = "PathBasedRouting"
    http_listener_name         = local.listener_name
    url_path_map_name          = local.management_api_url_path_map_name_pool_name
  }

  url_path_map {
    name = local.management_api_url_path_map_name_pool_name
    default_backend_address_pool_name  = local.backend_address_pool_name
    default_backend_http_settings_name = local.http_setting_name

    path_rule {
      name = "api"
      paths = ["/api/*", "/docs*", "/openapi.json"]
      backend_address_pool_name = local.management_api_backend_address_pool_name
      backend_http_settings_name = local.http_setting_name
    } 
  }
}

data "azurerm_public_ip" "appgwpip_data" {
  name                  = "pip-agw-${var.resource_name_prefix}-${var.environment}-${var.tre_id}"
  resource_group_name   = var.resource_group_name
}

output "app_gateway_fqdn" {
  value = "https://${data.azurerm_public_ip.appgwpip_data.fqdn}"
}