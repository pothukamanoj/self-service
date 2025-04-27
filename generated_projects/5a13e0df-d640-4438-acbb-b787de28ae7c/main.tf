module "storage_account" {
  source = "../modules/storage_account"
  name = "s name"
  location = "eastuse"
  resource_group_name = "rg"
  account_tier = "ad"
}

module "virtual_network" {
  source = "../modules/virtual_network"
  name = "dsd"
  address_space = "sf"
  location = "fs"
  resource_group_name = "fsf"
}

