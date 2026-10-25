package main

import rego.v1

# Helpers shared by all plan policies. Input is the JSON from:
#   tofu plan -out tfplan && tofu show -json tfplan > plan.json

# Resources of a given type that the plan creates or updates (not deletes).
managed(type) := {rc |
	some rc in input.resource_changes
	rc.mode == "managed"
	rc.type == type
	rc.change.after != null
}

open_cidr := "0.0.0.0/0"

valid_envs := {"dev", "prod"}

required_tags := {"app", "env", "owner"}

# Resource types that must carry the required tags.
taggable := {"aws_db_instance", "aws_eks_cluster"}

env_of(rc) := rc.change.after.tags.env

has_tag(rc, tag) if rc.change.after.tags[tag]

# COMMON-001: required tags
deny contains msg if {
	some t in taggable
	some rc in managed(t)
	some tag in required_tags
	not has_tag(rc, tag)
	msg := sprintf("COMMON-001: %s is missing required tag '%s'", [rc.address, tag])
}

# COMMON-002: env tag must be a known environment
deny contains msg if {
	some t in taggable
	some rc in managed(t)
	env := env_of(rc)
	not env in valid_envs
	msg := sprintf("COMMON-002: %s has unknown env '%s' (allowed: dev, prod)", [rc.address, env])
}
