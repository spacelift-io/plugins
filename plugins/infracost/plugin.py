from spaceforge import SpaceforgePlugin, Parameter, Variable, Context, Policy

class InfracostPlugin(SpaceforgePlugin):
    """
    A plugin for integrating with Infracost to estimate costs of infrastructure changes.
    """

    # Plugin metadata
    __plugin_name__ = "Infracost"
    __labels__ = ["cost estimation", "infrastructure"]
    __version__ = "1.0.0"
    __author__ = "Spacelift Team"

    __parameters__ = [
        Parameter(
            name="Infracost API Key",
            id="infracost_api_key",
            description="The API key for Infracost authentication",
            required=True,
            sensitive=True
        )
    ]

    __contexts__ = [
        Context(
            name_prefix="INFRACOST",
            description="Infracost Plugin",
            env=[
                Variable(
                    key="INFRACOST_API_KEY",
                    value_from_parameter="Infracost API Key",
                    sensitive=True
                )
            ],
            hooks={
                "after_plan": [
                    "infracost breakdown --path . --out-file infracost.custom.spacelift.json --format json"
                ]
            }
        )
    ]

    __policies__ = [
        Policy(
            name_prefix="INFRACOST",
            type="PLAN",
            body="""
package spacelift

# This example plan policy demonstrates using data from infracost to
# ensure that resources can't be created if their mostly cost is greater than
# a specific threshold while displaying a warning if their cost is above
# a different threshold.
#
# You can read more about plan policies here:
# https://docs.spacelift.io/concepts/policy/terraform-plan-policy

# Prevent any changes that will cause the monthly cost to go above a certain threshold
deny[sprintf("monthly cost greater than $%d ($%.2f)", [threshold, monthly_cost])] {
	threshold := 100
	monthly_cost := to_number(input.third_party_metadata.infracost.projects[0].breakdown.totalMonthlyCost)
	monthly_cost > threshold
}

# Warn if the monthly costs increase more than a certain percentage
warn[sprintf("monthly cost increase greater than %d%% (%.2f%%)", [threshold, percentage_increase])] {
	threshold := 5
	previous_cost := to_number(input.third_party_metadata.infracost.projects[0].pastBreakdown.totalMonthlyCost)
	previous_cost > 0

	monthly_cost := to_number(input.third_party_metadata.infracost.projects[0].breakdown.totalMonthlyCost)
	percentage_increase := ((monthly_cost - previous_cost) / previous_cost) * 100

	percentage_increase > threshold
}

# Learn more about sampling policy evaluations here:
# https://docs.spacelift.io/concepts/policy#sampling-policy-inputs
sample := true
""",
        )
    ]