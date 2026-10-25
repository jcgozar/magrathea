package main

import rego.v1

# Domain platform standard (standards/domain-platform.md).
#
# The mode comes from a data file the project's CI writes from magrathea.json:
#   python3 .magrathea/scripts/magrathea_lock.py mode-data --out .mode.json
#   conftest test ... --data .mode.json plan.json
# The file is {"magrathea": {"infra_mode": ..., "domain": ..., "type": ...}}. Without the file,
# or with infra_mode "standalone", nothing here fires. It fires only on an explicit "domain" mode
# that names a domain, so existing projects are not affected.

# Resource types that belong to the shared infrastructure of a domain platform. Starting list;
# extend it with a Magrathea request.
shared_types := {
	"aws_eks_cluster",
	"aws_eks_node_group",
	"aws_eks_fargate_profile",
	"aws_eks_addon",
	"aws_launch_template",
	"aws_vpc",
	"aws_subnet",
	"aws_internet_gateway",
	"aws_nat_gateway",
	"aws_route_table",
	"aws_route",
	"aws_eks_access_entry",
	"aws_iam_openid_connect_provider",
}

domain_mode if {
	data.magrathea.infra_mode == "domain"
	is_string(data.magrathea.domain)
	data.magrathea.domain != ""
}

# DOMAIN-001: a project in domain mode does not create shared infrastructure
deny contains msg if {
	domain_mode
	some t in shared_types
	some rc in managed(t)
	msg := sprintf("DOMAIN-001: %s creates shared infrastructure (%s); this project attaches to the domain platform '%s'. Ask its operator, do not create it here", [rc.address, t, data.magrathea.domain])
}
