# This Terraform configuration creates a Flex Consumption plan app in Azure Functions 
# with the required Storage account and Blob Storage deployment container.
# It also creates an Azure SQL db with firewall rules to allow your IP 
# and azure services to access.
#
# Also adds the required env vars for New Relic APM 
#

# Create a random pet to generate a unique resource group name
resource "random_pet" "rg_name" {
  prefix = var.resource_group_name_prefix
}

# Create a resource group
resource "azurerm_resource_group" "example" {
  location = var.resource_group_location
  name     = random_pet.rg_name.id
}

# Random String for unique naming of resources
resource "random_string" "name" {
  length  = 8
  special = false
  upper   = false
  lower   = true
  numeric = false
}

# Create a storage account
resource "azurerm_storage_account" "example" {
  name                     = coalesce(var.sa_name, random_string.name.result)
  resource_group_name      = azurerm_resource_group.example.name
  location                 = azurerm_resource_group.example.location
  account_tier             = var.sa_account_tier
  account_replication_type = var.sa_account_replication_type
}

# Create a storage container
resource "azurerm_storage_container" "example" {
  name                  = "example-flexcontainer"
  storage_account_id    = azurerm_storage_account.example.id
  container_access_type = "private"
}

# Create a Log Analytics workspace for Application Insights
resource "azurerm_log_analytics_workspace" "example" {
  name                = coalesce(var.ws_name, random_string.name.result)
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# Create an Application Insights instance for monitoring
resource "azurerm_application_insights" "example" {
  name                = coalesce(var.ai_name, random_string.name.result)
  location            = azurerm_resource_group.example.location
  resource_group_name = azurerm_resource_group.example.name
  application_type    = "web"
  workspace_id = azurerm_log_analytics_workspace.example.id
}

# Create a service plan
resource "azurerm_service_plan" "example" {
  name                = coalesce(var.asp_name, random_string.name.result)
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location
  sku_name            = "FC1"
  os_type             = "Linux"
}

# Create a function app
resource "azurerm_function_app_flex_consumption" "example" {
  name                = coalesce(var.fa_name, random_string.name.result)
  resource_group_name = azurerm_resource_group.example.name
  location            = azurerm_resource_group.example.location
  service_plan_id     = azurerm_service_plan.example.id

  storage_container_type      = "blobContainer"
  storage_container_endpoint  = "${azurerm_storage_account.example.primary_blob_endpoint}${azurerm_storage_container.example.name}"
  storage_authentication_type = "StorageAccountConnectionString"
  storage_access_key          = azurerm_storage_account.example.primary_access_key
  runtime_name                = var.runtime_name
  runtime_version             = var.runtime_version
  maximum_instance_count      = 50
  instance_memory_in_mb       = 2048
  
  app_settings = {
  "DB_SERVER"             = azurerm_mssql_server.server.name
  "DB_DATABASE"           = "AdventureWorks"
  "DB_USERNAME"           = "azureadmin"
  "MSSQL_SA_PASSWORD"     = var.admin_password
  "NEW_RELIC_LICENSE_KEY" = var.new_relic_license_key
  "NEW_RELIC_APP_NAME"    = var.new_relic_app_name
  }
 
 site_config {
   }
}

resource "random_password" "admin_password" {
  count       = var.admin_password == null ? 1 : 0
  length      = 20
  special     = true
  min_numeric = 1
  min_upper   = 1
  min_lower   = 1
  min_special = 1
}

resource "random_pet" "azurerm_mssql_server_name" {
  prefix = "sql"
}

resource "azurerm_mssql_server" "server" {
  name                         = random_pet.azurerm_mssql_server_name.id
  resource_group_name          = azurerm_resource_group.example.name
  location                     = azurerm_resource_group.example.location
  administrator_login          = var.admin_username
  administrator_login_password = var.admin_password
  version                      = "12.0"
}

# Create an Azure SQL Database with AdventureWorksLT sample data
resource "azurerm_mssql_database" "example" {
  name                = "AdventureWorks"
  server_id           = azurerm_mssql_server.server.id
  sample_name  = "AdventureWorksLT" # This enables the sample data
}

resource "azurerm_mssql_database" "db" {
  name      = var.sql_db_name
  server_id = azurerm_mssql_server.server.id
}

resource "azurerm_mssql_firewall_rule" "example" {
  name             = "allow-my-ip-address"
  server_id        = azurerm_mssql_server.server.id
  start_ip_address = var.my_ip_address_start
  end_ip_address   = var.my_ip_address_end
}

resource "azurerm_mssql_firewall_rule" "appServiceIP" {
  name                = "AllowAccessFromAzure"
  server_id           = azurerm_mssql_server.server.id
  start_ip_address    = "0.0.0.0"
  end_ip_address      = "0.0.0.0"
}