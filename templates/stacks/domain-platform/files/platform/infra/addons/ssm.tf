# Published interface (DOMAIN-010): identifiers only, never secrets. Renaming or removing a
# parameter breaks every project of this domain; see docs/domain-platform/README.md.
# TODO: replace each variable with the attribute of the resource this area creates once it exists.

variable "ingress_class" {
  type        = string
  description = "TODO: the ingress class (an identifier)."
}

resource "aws_ssm_parameter" "ingress_class" {
  name  = "/${var.domain}/${var.region}/platform/ingress-class"
  type  = "String"
  value = var.ingress_class
}
