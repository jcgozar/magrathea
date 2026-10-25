# Published interface (DOMAIN-010): identifiers only, never secrets. Renaming or removing a
# parameter breaks every project of this domain; see docs/domain-platform/README.md.
# TODO: replace each variable with the attribute of the resource this area creates once it exists.

variable "vpc_id" {
  type        = string
  description = "TODO: the vpc id (an identifier)."
}

resource "aws_ssm_parameter" "vpc_id" {
  name  = "/${var.domain}/${var.region}/platform/vpc-id"
  type  = "String"
  value = var.vpc_id
}

variable "private_subnet_ids" {
  type        = list(string)
  description = "TODO: the private subnet ids (an identifier)."
}

resource "aws_ssm_parameter" "private_subnet_ids" {
  name  = "/${var.domain}/${var.region}/platform/private-subnet-ids"
  type  = "StringList"
  value = join(",", var.private_subnet_ids)
}

variable "public_subnet_ids" {
  type        = list(string)
  description = "TODO: the public subnet ids (an identifier)."
}

resource "aws_ssm_parameter" "public_subnet_ids" {
  name  = "/${var.domain}/${var.region}/platform/public-subnet-ids"
  type  = "StringList"
  value = join(",", var.public_subnet_ids)
}
