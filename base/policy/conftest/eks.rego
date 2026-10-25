package main

import rego.v1

# EKS cluster standard (standards/eks-cluster.md).

clusters := managed("aws_eks_cluster")

vpc_cfg(rc) := rc.change.after.vpc_config[0]

public_cidrs(cfg) := object.get(cfg, "public_access_cidrs", null)

exposed(cfg) if public_cidrs(cfg) == null

exposed(cfg) if count(public_cidrs(cfg)) == 0

exposed(cfg) if open_cidr in public_cidrs(cfg)

# K8S-001: the API endpoint is private, or public access is limited to listed CIDRs
deny contains msg if {
	some rc in clusters
	cfg := vpc_cfg(rc)
	cfg.endpoint_public_access == true
	exposed(cfg)
	msg := sprintf("K8S-001: %s exposes the API endpoint to the internet; set public_access_cidrs or disable public access", [rc.address])
}

# K8S-002: secrets encryption with KMS, and every control-plane log type enabled
required_logs := {"api", "audit", "authenticator", "controllerManager", "scheduler"}

encrypts_secrets(rc) if {
	some cfg in object.get(rc.change.after, "encryption_config", [])
	"secrets" in cfg.resources
}

deny contains msg if {
	some rc in clusters
	not encrypts_secrets(rc)
	msg := sprintf("K8S-002: %s must encrypt secrets with a KMS key (encryption_config)", [rc.address])
}

deny contains msg if {
	some rc in clusters
	enabled := {l | some l in object.get(rc.change.after, "enabled_cluster_log_types", [])}
	missing := required_logs - enabled
	count(missing) > 0
	msg := sprintf("K8S-002: %s is missing control-plane log types: %v", [rc.address, sort(missing)])
}

# K8S-003: workloads use IRSA or EKS Pod Identity, never static IAM access keys
deny contains msg if {
	some rc in managed("aws_iam_access_key")
	msg := sprintf("K8S-003: %s creates a static IAM access key; use IRSA or EKS Pod Identity", [rc.address])
}

# K8S-004: node launch templates require IMDSv2
imds_required(rc) if {
	some m in object.get(rc.change.after, "metadata_options", [])
	m.http_tokens == "required"
}

deny contains msg if {
	some rc in managed("aws_launch_template")
	not imds_required(rc)
	msg := sprintf("K8S-004: %s must set metadata_options.http_tokens = \"required\" (IMDSv2)", [rc.address])
}
