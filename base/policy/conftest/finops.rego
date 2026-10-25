package main

import rego.v1

# FinOps standard (standards/finops.md). A plan cannot show that a budget is missing, so this
# checks only the budgets it contains. Attribute names follow the AWS provider's
# aws_budgets_budget (TODO: verify against the provider version a project pins).

# A notification block counts when it names an email address or an SNS topic.
has_subscriber(n) if count(n.subscriber_email_addresses) > 0

has_subscriber(n) if count(n.subscriber_sns_topic_arns) > 0

# A subscriber known only after apply (a topic created in the same plan) also counts.
unknown_subscriber(rc) if rc.change.after_unknown.notification == true

unknown_subscriber(rc) if {
	some n in rc.change.after_unknown.notification
	n.subscriber_sns_topic_arns == true
}

unknown_subscriber(rc) if {
	some n in rc.change.after_unknown.notification
	n.subscriber_email_addresses == true
}

budget_notifies(rc) if {
	some n in rc.change.after.notification
	has_subscriber(n)
}

budget_notifies(rc) if unknown_subscriber(rc)

# FIN-009 (SHOULD): every budget notifies someone
warn contains msg if {
	some rc in managed("aws_budgets_budget")
	not budget_notifies(rc)
	msg := sprintf("FIN-009: %s should have a notification with an email or SNS topic subscriber", [rc.address])
}
