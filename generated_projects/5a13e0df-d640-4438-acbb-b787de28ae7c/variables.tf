variable "storage_account_name" {
  description = "The name of the storage account"
  type        = string
}

variable "storage_account_location" {
  description = "The Azure region to deploy the storage account"
  type        = string
}

variable "storage_account_resource_group_name" {
  description = "The name of the resource group"
  type        = string
}

variable "storage_account_account_tier" {
  description = "The tier of the storage account"
  type        = string
}

variable "virtual_network_name" {
  description = "The name of the virtual network"
  type        = string
}

variable "virtual_network_address_space" {
  description = "The address space of the virtual network"
  type        = list(string)
}

variable "virtual_network_location" {
  description = "The Azure region to deploy the virtual network"
  type        = string
}

variable "virtual_network_resource_group_name" {
  description = "The name of the resource group"
  type        = string
}

