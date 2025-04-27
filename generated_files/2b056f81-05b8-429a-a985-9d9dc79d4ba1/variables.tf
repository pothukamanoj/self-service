variable "name" {
  description = "The name of the storage account"
  type        = string
}

variable "location" {
  description = "The location of the storage account"
  type        = string
}

variable "tags" {
  description = "A set of tags to assign to the resource"
  type        = map(string)
  default     = ""
}

