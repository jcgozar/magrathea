# eks area of the domain platform '@@domain@@'. NOT READY TO APPLY: resolve every TODO first.
# One state per area; apply order is global, network, eks, addons (ADR 0009).

terraform {
  # TODO: set required_version and pin the aws provider version after checking what the operator runs.
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }

  # TODO: state bucket, key (one per area), region and locking. Access to the state is the operator's
  # alone. Supply the values at init time (tofu init -backend-config=...), never commit credentials.
  backend "s3" {}
}

provider "aws" {
  region = var.region

  default_tags {
    tags = local.tags
  }
}

locals {
  # COMMON-001 / COMMON-002: app, env and owner on everything that can carry tags.
  tags = {
    app   = "@@slug@@"
    env   = var.env
    owner = var.owner
  }
}
