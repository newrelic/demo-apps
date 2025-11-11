variable "resource_group_name" {
  type        = string
  default     = ""
  description = "The name of the Azure resource group. If blank, a random name will be generated."
}

variable "resource_group_name_prefix" {
  type        = string
  default     = "rg"
  description = "Prefix of the resource group name that's combined with a random ID so name is unique in your Azure subscription."
}

variable "resource_group_location" {
  type        = string
  default     = "eastus2"
  description = "Location of the resource group."
}

variable "sa_account_tier" {
  description = "The tier of the storage account. Possible values are Standard and Premium."
  type        = string
  default     = "Standard"
}

variable "sa_account_replication_type" {
  description = "The replication type of the storage account. Possible values are LRS, GRS, RAGRS, and ZRS."
  type        = string
  default     = "LRS"
}

variable "sa_name" {
  description = "The name of the storage account. If blank, a random name will be generated."
  type        = string
  default     = ""
}

variable "ws_name" {
  description = "The name of the Log Analytics workspace. If blank, a random name will be generated."
  type        = string
  default     = ""
}

variable "ai_name" {
  description = "The name of the Application Insights instance. If blank, a random name will be generated."
  type        = string
  default     = ""
}

variable "asp_name" {
  description = "The name of the App Service Plan. If blank, a random name will be generated."
  type        = string
  default     = ""
}

variable "fa_name" {
  description = "The name of the Function App. If blank, a random name will be generated."
  type        = string
  default     = ""
}

variable "runtime_name" {
  description = "The name of the language worker runtime."
  type        = string
  default     = "node" # Allowed: dotnet-isolated, java, node, powershell, python
}

variable "runtime_version" {
  description = "The version of the language worker runtime."
  type        = string
  default     = "20" # Supported versions: see https://aka.ms/flexfxversions
}

variable "sql_db_name" {
  type        = string
  description = "The name of the SQL Database."
  default     = "SampleDB"
}

variable "admin_username" {
  type        = string
  description = "The administrator username of the SQL logical server."
  default     = "azureadmin"
}

variable "admin_password" {
  type        = string
  description = "The administrator password of the SQL logical server."
  sensitive   = true
  default     = null
}

variable "new_relic_license_key" {
  description = "Your New Relic Ingest License Key."
  type        = string
  sensitive   = true
}

variable "new_relic_team_tag" {
  description = "Value of 'nr.team' tag."
  type        = string
  default     = ""
}

variable "new_relic_environment_tag" {
  description = "Value of 'environment' tag."
  type        = string
  default     = "staging"
}

variable "new_relic_app_name" {
  description = "App Name in New Relic"
  type        = string
}

variable "my_ip_address_start" {
  description = "Your local public IP address to allow SSH and web access."
  type        = string
}

variable "my_ip_address_end" {
  description = "Your local public IP address to allow SSH and web access."
  type        = string
}