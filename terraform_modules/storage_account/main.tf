resource "azurerm_storage_account" "example" {
  name                     = var.name
  location                 = var.location
  resource_group_name      = var.resource_group_name
  account_tier              = var.account_tier
  account_replication_type = "LRS"
}
