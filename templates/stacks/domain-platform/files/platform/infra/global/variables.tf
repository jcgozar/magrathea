variable "domain" {
  type    = string
  default = "@@domain@@"
}

variable "region" {
  type        = string
  description = "TODO: the region this domain platform instance serves. One instance per region."
}

variable "env" {
  type        = string
  description = "TODO: dev or prod (COMMON-002)."
}

variable "owner" {
  type    = string
  default = "@@owner@@"
}
