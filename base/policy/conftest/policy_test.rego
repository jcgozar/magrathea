package main_test

import data.main
import rego.v1

# --- helpers -----------------------------------------------------------

change(type, name, after) := {
	"address": sprintf("%s.%s", [type, name]),
	"mode": "managed",
	"type": type,
	"name": name,
	"change": {"actions": ["create"], "after": after},
}

plan(changes) := {"resource_changes": changes}

# True if any message starts with "<id>:".
has_rule(msgs, id) if {
	some m in msgs
	startswith(m, concat("", [id, ":"]))
}

tags(env) := {"app": "ingest", "env": env, "owner": "platform"}

# --- fixtures: compliant resources -------------------------------------

good_pg := {
	"engine": "postgres",
	"instance_class": "db.t4g.small",
	"allocated_storage": 20,
	"max_allocated_storage": 50,
	"storage_encrypted": true,
	"publicly_accessible": false,
	"manage_master_user_password": true,
	"backup_retention_period": 7,
	"multi_az": false,
	"deletion_protection": false,
	"skip_final_snapshot": false,
	"auto_minor_version_upgrade": true,
	"parameter_group_name": "pg-force-ssl",
	"tags": tags("dev"),
}

good_pg_prod := object.union(good_pg, {
	"instance_class": "db.t4g.large",
	"multi_az": true,
	"deletion_protection": true,
	"tags": tags("prod"),
})

good_param_group := {
	"family": "postgres16",
	"parameter": [{"name": "rds.force_ssl", "value": "1"}],
}

good_cluster := {
	"vpc_config": [{
		"endpoint_private_access": true,
		"endpoint_public_access": true,
		"public_access_cidrs": ["203.0.113.0/24"],
	}],
	"encryption_config": [{"resources": ["secrets"]}],
	"enabled_cluster_log_types": ["api", "audit", "authenticator", "controllerManager", "scheduler"],
	"tags": tags("dev"),
}

pg_plan(after) := plan([change("aws_db_instance", "app", after)])

eks_plan(after) := plan([change("aws_eks_cluster", "main", after)])

# --- compliant resources raise nothing ---------------------------------

test_good_pg_dev_passes if {
	count(main.deny) == 0 with input as pg_plan(good_pg)
	count(main.warn) == 0 with input as pg_plan(good_pg)
}

test_good_pg_prod_passes if {
	count(main.deny) == 0 with input as pg_plan(good_pg_prod)
}

test_good_param_group_passes if {
	count(main.deny) == 0 with input as plan([change("aws_db_parameter_group", "pg", good_param_group)])
}

test_good_cluster_passes if {
	count(main.deny) == 0 with input as eks_plan(good_cluster)
}

# --- deletes are ignored -----------------------------------------------

test_deleted_resource_ignored if {
	deleted := {
		"address": "aws_db_instance.app",
		"mode": "managed",
		"type": "aws_db_instance",
		"change": {"actions": ["delete"], "after": null},
	}
	count(main.deny) == 0 with input as plan([deleted])
}

# --- COMMON ------------------------------------------------------------

test_common_001_missing_tag if {
	# object.union merges deeply, so drop the tags first
	after := object.union(object.remove(good_pg, ["tags"]), {"tags": {"app": "ingest", "env": "dev"}})
	has_rule(main.deny, "COMMON-001") with input as pg_plan(after)
}

test_common_002_unknown_env if {
	after := object.union(good_pg, {"tags": tags("staging")})
	has_rule(main.deny, "COMMON-002") with input as pg_plan(after)
}

# --- Postgres ----------------------------------------------------------

test_pg_001_unencrypted if {
	after := object.union(good_pg, {"storage_encrypted": false})
	has_rule(main.deny, "PG-001") with input as pg_plan(after)
}

test_pg_001_no_parameter_group if {
	after := object.remove(good_pg, ["parameter_group_name"])
	has_rule(main.deny, "PG-001") with input as pg_plan(after)
}

test_pg_001_parameter_group_without_force_ssl if {
	pg := {"family": "postgres16", "parameter": [{"name": "log_statement", "value": "ddl"}]}
	has_rule(main.deny, "PG-001") with input as plan([change("aws_db_parameter_group", "pg", pg)])
}

test_pg_002_public if {
	after := object.union(good_pg, {"publicly_accessible": true})
	has_rule(main.deny, "PG-002") with input as pg_plan(after)
}

test_pg_003_open_security_group_rule if {
	rule := {
		"type": "ingress",
		"from_port": 5432,
		"to_port": 5432,
		"protocol": "tcp",
		"cidr_blocks": ["0.0.0.0/0"],
	}
	has_rule(main.deny, "PG-003") with input as plan([change("aws_security_group_rule", "db", rule)])
}

test_pg_003_open_all_traffic_rule if {
	rule := {"cidr_ipv4": "0.0.0.0/0", "ip_protocol": "-1"}
	has_rule(main.deny, "PG-003") with input as plan([change("aws_vpc_security_group_ingress_rule", "db", rule)])
}

test_pg_003_private_rule_passes if {
	rule := {
		"type": "ingress",
		"from_port": 5432,
		"to_port": 5432,
		"protocol": "tcp",
		"cidr_blocks": ["10.0.0.0/16"],
	}
	not has_rule(main.deny, "PG-003") with input as plan([change("aws_security_group_rule", "db", rule)])
}

test_pg_004_unmanaged_password if {
	after := object.union(good_pg, {"manage_master_user_password": false})
	has_rule(main.deny, "PG-004") with input as pg_plan(after)
}

test_pg_005_dev_needs_backups if {
	after := object.union(good_pg, {"backup_retention_period": 0})
	has_rule(main.deny, "PG-005") with input as pg_plan(after)
}

test_pg_005_prod_short_backup if {
	after := object.union(good_pg_prod, {"backup_retention_period": 3})
	has_rule(main.deny, "PG-005") with input as pg_plan(after)
}

test_pg_005_prod_needs_multi_az if {
	after := object.union(good_pg_prod, {"multi_az": false})
	has_rule(main.deny, "PG-005") with input as pg_plan(after)
}

test_pg_005_prod_needs_deletion_protection if {
	after := object.union(good_pg_prod, {"deletion_protection": false})
	has_rule(main.deny, "PG-005") with input as pg_plan(after)
}

test_pg_005_prod_final_snapshot if {
	after := object.union(good_pg_prod, {"skip_final_snapshot": true})
	has_rule(main.deny, "PG-005") with input as pg_plan(after)
}

test_pg_006_class_not_allowed_in_dev if {
	after := object.union(good_pg, {"instance_class": "db.r6g.4xlarge"})
	has_rule(main.deny, "PG-006") with input as pg_plan(after)
}

test_pg_006_class_allowed_in_prod_not_dev if {
	after := object.union(good_pg, {"instance_class": "db.m6g.large"})
	has_rule(main.deny, "PG-006") with input as pg_plan(after)
}

test_pg_006_storage_above_limit if {
	after := object.union(good_pg, {"allocated_storage": 500})
	has_rule(main.deny, "PG-006") with input as pg_plan(after)
}

test_pg_006_autoscaling_ceiling_above_limit if {
	after := object.union(good_pg, {"max_allocated_storage": 1000})
	has_rule(main.deny, "PG-006") with input as pg_plan(after)
}

test_pg_007_warns_without_minor_upgrades if {
	after := object.union(good_pg, {"auto_minor_version_upgrade": false})
	has_rule(main.warn, "PG-007") with input as pg_plan(after)
	count(main.deny) == 0 with input as pg_plan(after)
}

# --- EKS ---------------------------------------------------------------

test_k8s_001_open_cidr if {
	after := object.union(good_cluster, {"vpc_config": [{
		"endpoint_public_access": true,
		"public_access_cidrs": ["0.0.0.0/0"],
	}]})
	has_rule(main.deny, "K8S-001") with input as eks_plan(after)
}

test_k8s_001_default_cidrs if {
	after := object.union(good_cluster, {"vpc_config": [{"endpoint_public_access": true}]})
	has_rule(main.deny, "K8S-001") with input as eks_plan(after)
}

test_k8s_001_private_only_passes if {
	after := object.union(good_cluster, {"vpc_config": [{
		"endpoint_private_access": true,
		"endpoint_public_access": false,
	}]})
	not has_rule(main.deny, "K8S-001") with input as eks_plan(after)
}

test_k8s_002_no_secrets_encryption if {
	after := object.remove(good_cluster, ["encryption_config"])
	has_rule(main.deny, "K8S-002") with input as eks_plan(after)
}

test_k8s_002_missing_log_type if {
	after := object.union(good_cluster, {"enabled_cluster_log_types": ["api", "audit"]})
	has_rule(main.deny, "K8S-002") with input as eks_plan(after)
}

test_k8s_003_static_access_key if {
	has_rule(main.deny, "K8S-003") with input as plan([change("aws_iam_access_key", "app", {"user": "app"})])
}

test_k8s_004_imds_optional if {
	lt := {"metadata_options": [{"http_tokens": "optional"}]}
	has_rule(main.deny, "K8S-004") with input as plan([change("aws_launch_template", "nodes", lt)])
}

test_k8s_004_imds_required_passes if {
	lt := {"metadata_options": [{"http_tokens": "required"}]}
	not has_rule(main.deny, "K8S-004") with input as plan([change("aws_launch_template", "nodes", lt)])
}

# --- FinOps ------------------------------------------------------------

good_budget := {
	"name": "app-dev-monthly",
	"budget_type": "COST",
	"limit_amount": "100",
	"limit_unit": "USD",
	"time_unit": "MONTHLY",
	"notification": [{
		"comparison_operator": "GREATER_THAN",
		"threshold": 80,
		"threshold_type": "PERCENTAGE",
		"notification_type": "ACTUAL",
		"subscriber_email_addresses": ["owner@example.com"],
		"subscriber_sns_topic_arns": null,
	}],
}

budget_plan(after) := plan([change("aws_budgets_budget", "app", after)])

test_fin_009_budget_with_email_passes if {
	count(main.warn) == 0 with input as budget_plan(good_budget)
}

test_fin_009_budget_with_sns_passes if {
	after := object.union(good_budget, {"notification": [{
		"subscriber_email_addresses": null,
		"subscriber_sns_topic_arns": ["arn:aws:sns:us-east-1:111111111111:budget"],
	}]})
	not has_rule(main.warn, "FIN-009") with input as budget_plan(after)
}

test_fin_009_budget_with_topic_unknown_until_apply_passes if {
	after := object.union(good_budget, {"notification": [{
		"subscriber_email_addresses": null,
		"subscriber_sns_topic_arns": null,
	}]})
	rc := object.union(change("aws_budgets_budget", "app", after), {"change": {
		"actions": ["create"],
		"after": after,
		"after_unknown": {"notification": [{"subscriber_sns_topic_arns": true}]},
	}})
	not has_rule(main.warn, "FIN-009") with input as plan([rc])
}

test_fin_009_budget_without_notification if {
	after := object.remove(good_budget, ["notification"])
	has_rule(main.warn, "FIN-009") with input as budget_plan(after)
}

test_fin_009_notification_without_subscriber if {
	after := object.union(good_budget, {"notification": [{
		"subscriber_email_addresses": [],
		"subscriber_sns_topic_arns": null,
	}]})
	has_rule(main.warn, "FIN-009") with input as budget_plan(after)
}

# --- DOMAIN-001: shared infrastructure in domain mode ---------------------

domain_data := {"magrathea": {"infra_mode": "domain", "domain": "payments"}}

cluster_plan := plan([
	change("aws_eks_cluster", "shared", {"tags": tags("dev"), "vpc_config": [{"endpoint_public_access": false}], "encryption_config": [{"resources": ["secrets"]}], "enabled_cluster_log_types": ["api", "audit", "authenticator", "controllerManager", "scheduler"]}),
	change("aws_vpc", "main", {"cidr_block": "10.0.0.0/16"}),
])

test_domain_001_fails_in_domain_mode if {
	msgs := main.deny with input as cluster_plan with data.magrathea as domain_data.magrathea
	has_rule(msgs, "DOMAIN-001")
	count({m | some m in msgs; startswith(m, "DOMAIN-001:")}) == 2
}

test_domain_001_covers_routes_and_cluster_access_entries if {
	p := plan([
		change("aws_route", "default", {"destination_cidr_block": "0.0.0.0/0"}),
		change("aws_eks_access_entry", "admin", {"principal_arn": "arn:aws:iam::111111111111:role/x"}),
	])
	msgs := main.deny with input as p with data.magrathea as domain_data.magrathea
	count({m | some m in msgs; startswith(m, "DOMAIN-001:")}) == 2
}

test_domain_001_passes_for_project_resources_in_domain_mode if {
	p := plan([change("aws_ssm_parameter", "x", {"name": "/payments/eu-west-1/app/x"})])
	msgs := main.deny with input as p with data.magrathea as domain_data.magrathea
	not has_rule(msgs, "DOMAIN-001")
}

test_domain_001_silent_when_standalone if {
	msgs := main.deny with input as cluster_plan with data.magrathea as {"infra_mode": "standalone"}
	not has_rule(msgs, "DOMAIN-001")
}

test_domain_001_silent_without_mode_data if {
	msgs := main.deny with input as cluster_plan
	not has_rule(msgs, "DOMAIN-001")
}

test_domain_001_silent_in_a_domain_platform_repo if {
	msgs := main.deny with input as cluster_plan with data.magrathea as {"type": "domain-platform", "domain": "payments"}
	not has_rule(msgs, "DOMAIN-001")
}

test_domain_001_needs_a_domain_name if {
	msgs := main.deny with input as cluster_plan with data.magrathea as {"infra_mode": "domain"}
	not has_rule(msgs, "DOMAIN-001")
}

test_domain_001_ignores_a_delete if {
	p := plan([{"address": "aws_vpc.old", "mode": "managed", "type": "aws_vpc", "name": "old", "change": {"actions": ["delete"], "after": null}}])
	msgs := main.deny with input as p with data.magrathea as domain_data.magrathea
	not has_rule(msgs, "DOMAIN-001")
}
