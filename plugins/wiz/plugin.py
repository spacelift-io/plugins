import json
import os
import shutil

from spaceforge import Binary, Context, Parameter, Policy, SpaceforgePlugin, Variable


class WizPlugin(SpaceforgePlugin):
    """
    This adds the `wiz` plugin to your Spacelift account.
    It will scan your infrastructure as code (IaC) for vulnerabilities using Wiz CLI, generating a report of findings and
    adding them to the policy input.

    The scan runs after the plan phase, so it includes resolved Terraform modules and the exported plan file
    in the directory scan for broader coverage.

    ## Usage

    1. Spin up the plugin
    2. Add the autoattach label to any stack that has access to your decryption keys.

    The Wiz plugin scans your IaC files for vulnerabilities and generates a report.
    You can also access the data from a plan policy via the `input.third_party_metadata.custom.wiz` object.
    Samples of these policies are included with the plugin.
    """

    # Plugin metadata
    __plugin_name__ = "Wiz"
    __labels__ = ["security", "code scanning", "vulnerability"]
    __version__ = "3.0.0"
    __author__ = "Spacelift Team"

    __binaries__ = [
        Binary(
            name="wizcli",
            download_urls={
                "amd64": "https://downloads.wiz.io/v1/wizcli/latest/wizcli-linux-amd64",
                "arm64": "https://downloads.wiz.io/v1/wizcli/latest/wizcli-linux-arm64",
            },
        )
    ]

    # Plugin parameters
    __parameters__ = [
        Parameter(
            name="Default Scan Name",
            id="default_scan_name",
            description="The name of the scan that shows up in Wiz. If left empty, defaults to '{stack_id}-{run_id}'. This setting can be overridden on individual stacks by manually setting the environment variable (DEFAULT_SCAN_NAME) there",
            default="",
            type="string",
            required=False,
            sensitive=False,
        ),
        Parameter(
            name="Default Policies",
            id="default_policies",
            description="Comma separated list of policies to include in all scans. This setting can be overridden on individual stacks by manually setting the environment variable (DEFAULT_POLICIES) there.",
            default="",
            type="string",
            required=False,
            sensitive=False,
        ),
        Parameter(
            name="Wiz Client ID",
            id="wiz_client_id",
            description="The client ID for Wiz API authentication",
            type="string",
            required=True,
            sensitive=False,
        ),
        Parameter(
            name="Wiz Client Secret",
            id="wiz_client_secret",
            description="The client secret for Wiz API authentication",
            type="string",
            required=True,
            sensitive=True,
        ),
        Parameter(
            name="Additional Arguments",
            id="wiz_additional_args",
            description="Additional command-line arguments to pass to Wiz",
            default="",
            type="string",
            required=False,
        ),
        Parameter(
            name="Wiz CLI Autofail",
            id="wizcli_autofail",
            description="Allow wizcli to fail the run (instead of policies)",
            default=False,
            type="boolean",
            required=False,
            sensitive=False,
        ),
        Parameter(
            name="Is GovCloud",
            id="is_govcloud",
            description="Enable if you access wiz via gov.wiz.io",
            default=False,
            type="boolean",
            required=False,
            sensitive=False,
        ),
        Parameter(
            name="Is Fedramp",
            id="is_fedramp",
            description="Enable if you access wiz via app.wiz.us",
            default=False,
            type="boolean",
            required=False,
            sensitive=False,
        ),
    ]

    # Plugin contexts
    __contexts__ = [
        Context(
            name_prefix="WIZ",
            description="Wiz Plugin",
            env=[
                Variable(
                    key="DEFAULT_SCAN_NAME",
                    value_from_parameter="default_scan_name",
                    sensitive=False,
                ),
                Variable(
                    key="DEFAULT_POLICIES",
                    value_from_parameter="default_policies",
                    sensitive=False,
                ),
                Variable(
                    key="WIZ_CLIENT_ID",
                    value_from_parameter="wiz_client_id",
                    sensitive=False,
                ),
                Variable(
                    key="WIZ_CLIENT_SECRET",
                    value_from_parameter="wiz_client_secret",
                    sensitive=True,
                ),
                Variable(
                    key="WIZ_ADDITIONAL_ARGS",
                    value_from_parameter="wiz_additional_args",
                    sensitive=False,
                ),
                Variable(
                    key="WIZCLI_AUTOFAIL",
                    value_from_parameter="wizcli_autofail",
                    sensitive=False,
                ),
                Variable(
                    key="IS_GOVCLOUD",
                    value_from_parameter="is_govcloud",
                    sensitive=False,
                ),
                Variable(
                    key="IS_FEDRAMP",
                    value_from_parameter="is_fedramp",
                    sensitive=False,
                ),
            ],
        )
    ]

    __policies__ = [
        Policy(
            name_prefix="wiz_policy",
            type="PLAN",
            engine_type="REGO_V0",
            body="""
package spacelift

max_critical_vulnerabilities := 0
max_high_vulnerabilities := 0
max_medium_vulnerabilities := 3
max_low_vulnerabilities := 10

deny[sprintf("Too many critical vulnerabilities (%d)", [num])] {
	num := input.third_party_metadata.custom.wiz.result.scanStatistics.criticalMatches
    num > max_critical_vulnerabilities
}

deny[sprintf("Too many high vulnerabilities (%d)", [num])] {
	num := input.third_party_metadata.custom.wiz.result.scanStatistics.highMatches
    num > max_high_vulnerabilities
}

deny[sprintf("Too many medium vulnerabilities (%d)", [num])] {
	num := input.third_party_metadata.custom.wiz.result.scanStatistics.mediumMatches
    num > max_medium_vulnerabilities
}

deny[sprintf("Too many low vulnerabilities (%d)", [num])] {
	num := input.third_party_metadata.custom.wiz.result.scanStatistics.lowMatches
    num > max_low_vulnerabilities
}
            """,
            labels=["wiz-plugin"],
        )
    ]

    def __init__(self):
        super().__init__()

    def _get_iac_binary(self):
        """Detect whether tofu or terraform is available."""
        for binary in ["tofu", "terraform"]:
            if shutil.which(binary):
                return binary
        return None

    def _export_plan_json(self):
        """Export the Spacelift plan file to JSON so wizcli can scan it."""
        plan_file = "spacelift.plan"
        plan_json = "spacelift_plan.json"

        if not os.path.exists(plan_file):
            self.logger.warning(
                f"Plan file '{plan_file}' not found, skipping plan export"
            )
            return False

        iac_binary = self._get_iac_binary()
        if iac_binary is None:
            self.logger.warning(
                "Neither tofu nor terraform found in PATH, skipping plan export"
            )
            return False

        self.logger.info(f"Exporting plan file using {iac_binary}")
        return_code, stdout, stderr = self.run_cli(
            iac_binary, "show", "-no-color", "-json", plan_file, print_output=False
        )

        if return_code != 0:
            self.logger.warning(
                f"Failed to export plan JSON (exit code {return_code}), "
                "continuing with directory scan only"
            )
            return False

        with open(plan_json, "w") as f:
            f.write("\n".join(stdout))

        self.logger.info(f"Plan exported to {plan_json}")
        return True

    def _get_scan_name(self):
        """Get scan name from env var or auto-generate from stack/run IDs."""
        custom_name = os.environ.get("DEFAULT_SCAN_NAME", "").strip()
        if custom_name:
            return custom_name

        stack_id = os.environ.get("TF_VAR_spacelift_stack_id", "")
        run_id = os.environ.get("TF_VAR_spacelift_run_id", "")

        if stack_id and run_id:
            return f"{stack_id}-{run_id}"

        if stack_id:
            return stack_id

        return None

    def after_plan(self):
        self.logger.info("Scanning IaC after plan")

        if os.environ.get("IS_GOVCLOUD", "false").lower() == "true":
            os.environ["WIZ_ENV"] = "gov"

        if os.environ.get("IS_FEDRAMP", "false").lower() == "true":
            os.environ["WIZ_ENV"] = "fedramp"

        # Export plan file to JSON so wizcli includes it in the directory scan
        self._export_plan_json()

        args = [
            "wizcli",
            "scan",
            "dir",
            "./",
            "--json-output-file",
            "./wiz_scan.json",
            "--no-style",
            "--no-color",
            "--no-telemetry",
            "--no-browser",
            "--discovered-resources",
        ]

        scan_name = self._get_scan_name()
        if scan_name:
            args.extend(["--name", scan_name])

        if os.environ.get("DEFAULT_POLICIES", "") != "":
            policies = os.environ.get("DEFAULT_POLICIES").split(",")
            for policy in policies:
                args.extend(["-p", policy.strip()])

        additional_args = os.environ.get("WIZ_ADDITIONAL_ARGS", "").strip()
        if additional_args:
            args.extend(additional_args.split())

        return_code, stdout, stderr = self.run_cli(*args, print_output=False)
        if (
            os.environ.get("WIZCLI_AUTOFAIL", "false").lower() == "true"
            and return_code != 0
        ):
            # Print the output because we set print_output=False because wizcli outputs errors to stdout.
            for line in stdout:
                self.logger.error(line)
            exit(1)

        if return_code == 1:
            self.logger.error(
                "Wiz CLI Error: General error (timeout, network interruption, etc.)"
            )
            exit(1)

        if return_code == 2:
            self.logger.error("Wiz CLI Error: Invalid command-line arguments")
            exit(1)

        if return_code == 3:
            self.logger.error("Wiz CLI Error: Authentication issue.")
            exit(1)

        with open("wiz_scan.json", "r") as f:
            results = json.load(f)

        self.logger.debug(results)

        if results is None:
            self.logger.error("Failed to parse Wiz CLI output as JSON")
            self.logger.debug(stdout, results)
            exit(1)

        if "result" not in results or "ruleMatches" not in results["result"]:
            self.logger.error("Unexpected Wiz CLI output format")
            self.logger.debug(results)
            exit(1)

        self.add_to_policy_input("wiz", results)

        if results["result"]["ruleMatches"] is None:
            self.logger.info("No findings found in the IAC scan.")
        else:
            findings = {}
            # Sort the findings by the severity and their rule id
            for match in results["result"]["ruleMatches"]:
                if match["severity"] not in findings:
                    findings[match["severity"]] = {}
                if match["rule"]["id"] not in findings[match["severity"]]:
                    findings[match["severity"]][match["rule"]["id"]] = {
                        "rule": match["rule"],
                        "matches": [],
                    }
                findings[match["severity"]][match["rule"]["id"]]["matches"].append(
                    match
                )

            markdown = "# Wiz IAC Scan Findings\n\n"
            markdown += f"**Status:** {results['status']['state']} **Verdict:** {results['status']['verdict']}\n"
            for severity, matches in findings.items():
                severity = severity.upper()

                emoji = None
                if severity == "INFORMATIONAL":
                    emoji = "🟢"
                if severity == "LOW":
                    emoji = "🟡"
                elif severity == "MEDIUM":
                    emoji = "🟡"
                elif severity == "HIGH":
                    emoji = "🟠"
                elif severity == "CRITICAL":
                    emoji = "🔴"
                if emoji is not None:
                    markdown += f"### {emoji} {severity} Findings\n"
                else:
                    markdown += f"### {severity} Findings\n"

                for rule_id, rule_data in matches.items():
                    markdown += f"#### {rule_data['rule']['name']} (ID: {rule_id})\n"
                    for cycled_rule in rule_data["matches"]:
                        for match in cycled_rule["matches"]:
                            markdown += f"- File: {match['fileName']}, Line: {match['lineNumber']}\n"
                    markdown += "\n"
            if "reportUrl" in results:
                markdown += f"[View Report]({results['reportUrl']})\n"
            result = self.send_markdown(markdown)
            if not result:
                self.logger.error("Failed to send Wiz CLI output to spacelift")
