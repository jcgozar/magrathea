# Published interface (DOMAIN-010): identifiers only, never secrets. Renaming or removing a
# parameter breaks every project of this domain; see docs/domain-platform/README.md.
# TODO: replace each variable with the attribute of the resource this area creates once it exists.

variable "cluster_name" {
  type        = string
  description = "TODO: the cluster name (an identifier)."
}

resource "aws_ssm_parameter" "cluster_name" {
  name  = "/${var.domain}/${var.region}/platform/cluster-name"
  type  = "String"
  value = var.cluster_name
}

variable "oidc_provider_arn" {
  type        = string
  description = "TODO: the oidc provider arn (an identifier)."
}

resource "aws_ssm_parameter" "oidc_provider_arn" {
  name  = "/${var.domain}/${var.region}/platform/oidc-provider-arn"
  type  = "String"
  value = var.oidc_provider_arn
}
