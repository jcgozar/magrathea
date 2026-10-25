package main

import rego.v1

# Postgres standard (standards/postgres.md). Starting values: adjust to taste.

pg_limits := {
	"dev": {
		"classes": {"db.t4g.micro", "db.t4g.small", "db.t4g.medium"},
		"max_storage_gb": 50,
		"min_backup_days": 1,
	},
	"prod": {
		"classes": {"db.t4g.medium", "db.t4g.large", "db.m6g.large"},
		"max_storage_gb": 500,
		"min_backup_days": 7,
	},
}

pg_instances := {rc |
	some rc in managed("aws_db_instance")
	rc.change.after.engine == "postgres"
}

limits(rc) := pg_limits[env_of(rc)]

# PG-001: encrypted at rest
deny contains msg if {
	some rc in pg_instances
	not rc.change.after.storage_encrypted == true
	msg := sprintf("PG-001: %s must set storage_encrypted = true", [rc.address])
}

# PG-001: TLS required, via a parameter group that sets rds.force_ssl = 1
has_param_group(rc) if rc.change.after.parameter_group_name

has_param_group(rc) if rc.change.after_unknown.parameter_group_name == true

deny contains msg if {
	some rc in pg_instances
	not has_param_group(rc)
	msg := sprintf("PG-001: %s must use a parameter group that sets rds.force_ssl = 1", [rc.address])
}

force_ssl(rc) if {
	some p in rc.change.after.parameter
	p.name == "rds.force_ssl"
	p.value == "1"
}

deny contains msg if {
	some rc in managed("aws_db_parameter_group")
	startswith(rc.change.after.family, "postgres")
	not force_ssl(rc)
	msg := sprintf("PG-001: %s must set rds.force_ssl = 1", [rc.address])
}

# PG-002: never publicly accessible
deny contains msg if {
	some rc in pg_instances
	rc.change.after.publicly_accessible == true
	msg := sprintf("PG-002: %s must not be publicly accessible", [rc.address])
}

# PG-003: no ingress from the internet on the Postgres port
covers_pg(r) if {
	r.from_port <= 5432
	r.to_port >= 5432
}

covers_pg(r) if r.protocol == "-1"

covers_pg(r) if r.ip_protocol == "-1"

deny contains msg if {
	some rc in managed("aws_security_group_rule")
	rc.change.after.type == "ingress"
	covers_pg(rc.change.after)
	open_cidr in rc.change.after.cidr_blocks
	msg := sprintf("PG-003: %s opens Postgres (5432) to the internet", [rc.address])
}

deny contains msg if {
	some rc in managed("aws_vpc_security_group_ingress_rule")
	rc.change.after.cidr_ipv4 == open_cidr
	covers_pg(rc.change.after)
	msg := sprintf("PG-003: %s opens Postgres (5432) to the internet", [rc.address])
}

# PG-004: credentials managed by AWS Secrets Manager
# (the provider rejects a password alongside this setting, so one check is enough)
deny contains msg if {
	some rc in pg_instances
	not rc.change.after.manage_master_user_password == true
	msg := sprintf("PG-004: %s must set manage_master_user_password = true", [rc.address])
}

# PG-005: backups, and production safeguards
deny contains msg if {
	some rc in pg_instances
	lim := limits(rc)
	rc.change.after.backup_retention_period < lim.min_backup_days
	msg := sprintf("PG-005: %s needs backup_retention_period >= %d for env '%s'", [rc.address, lim.min_backup_days, env_of(rc)])
}

prod_pg := {rc |
	some rc in pg_instances
	env_of(rc) == "prod"
}

deny contains msg if {
	some rc in prod_pg
	not rc.change.after.multi_az == true
	msg := sprintf("PG-005: %s must be multi_az in prod", [rc.address])
}

deny contains msg if {
	some rc in prod_pg
	not rc.change.after.deletion_protection == true
	msg := sprintf("PG-005: %s must set deletion_protection in prod", [rc.address])
}

deny contains msg if {
	some rc in prod_pg
	rc.change.after.skip_final_snapshot == true
	msg := sprintf("PG-005: %s must not skip the final snapshot in prod", [rc.address])
}

# PG-006: instance class and storage ceiling come from the per-environment allowlist
allowed_class(rc, lim) if rc.change.after.instance_class in lim.classes

deny contains msg if {
	some rc in pg_instances
	lim := limits(rc)
	not allowed_class(rc, lim)
	msg := sprintf("PG-006: %s uses instance class '%s', not allowed in env '%s'", [rc.address, rc.change.after.instance_class, env_of(rc)])
}

deny contains msg if {
	some rc in pg_instances
	lim := limits(rc)
	rc.change.after.allocated_storage > lim.max_storage_gb
	msg := sprintf("PG-006: %s allocates %d GB, above the %d GB limit for env '%s'", [rc.address, rc.change.after.allocated_storage, lim.max_storage_gb, env_of(rc)])
}

deny contains msg if {
	some rc in pg_instances
	lim := limits(rc)
	rc.change.after.max_allocated_storage > lim.max_storage_gb
	msg := sprintf("PG-006: %s autoscaling ceiling %d GB is above the %d GB limit for env '%s'", [rc.address, rc.change.after.max_allocated_storage, lim.max_storage_gb, env_of(rc)])
}

# PG-007 (SHOULD): minor-version auto-upgrade
warn contains msg if {
	some rc in pg_instances
	not rc.change.after.auto_minor_version_upgrade == true
	msg := sprintf("PG-007: %s should enable auto_minor_version_upgrade", [rc.address])
}
