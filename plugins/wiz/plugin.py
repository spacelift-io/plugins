import json
import os

from spaceforge import SpaceforgePlugin, Parameter, Variable, Context, Policy, Binary


class WizPlugin(SpaceforgePlugin):
    """
# Plugin Wiz

This adds the `wiz` plugin to your Spacelift account.
It will scan your infrastructure as code (IaC) for vulnerabilities using Wiz CLI, generating a report of findings and
adding them to the policy input.

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
    __version__ = "1.0.0"
    __author__ = "Spacelift Team"

    __binaries__ = [
        Binary(
            name="wizcli",
            download_urls={
                "amd64": "https://downloads.wiz.io/wizcli/0.94.0/wizcli-linux-amd64",
                "arm64": "https://downloads.wiz.io/wizcli/0.94.0/wizcli-linux-arm64"
            }
        )
    ]

    # Plugin parameters
    __parameters__ = [
        Parameter(
            name="Wiz Client ID",
            id="wiz_client_id",
            description="The client ID for Wiz API authentication",
            required=True,
            sensitive=True
        ),
        Parameter(
            name="Wiz Client Secret",
            id="wiz_client_secret",
            description="The client secret for Wiz API authentication",
            required=True,
            sensitive=True
        )
    ]

    # Plugin contexts
    __contexts__ = [
        Context(
            name_prefix="WIZ",
            description="Wiz Plugin",
            env=[
                Variable(
                    key="WIZ_CLIENT_ID",
                    value_from_parameter="Wiz Client ID",
                    sensitive=True
                ),
                Variable(
                    key="WIZ_CLIENT_SECRET",
                    value_from_parameter="Wiz Client Secret",
                    sensitive=True
                ),
            ]
        )
    ]

    __policies__ = [
        Policy(
            name_prefix="wiz_policy",
            type="PLAN",
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
            labels=[
                "wiz-plugin"
            ]
        )
    ]

    def __init__(self):
        super().__init__()

    def before_plan(self):
        self.logger.info("Checking IAC Code")

        return_code, stdout, stderr = self.run_cli("wizcli", "auth", "--id", os.environ.get("WIZ_CLIENT_ID"),
                                                   "--secret", os.environ.get("WIZ_CLIENT_SECRET"))
        if return_code != 0:
            exit(1)

        return_code, stdout, stderr = self.run_cli("wizcli", "iac", "scan", "--format",
                                                   "json", "--path", "./", "--no-style", "--no-color", "--no-telemetry",
                                                   "--show-secret-snippets",
                                                   print_output=False)
        if return_code != 0:
            # Print the output because we set print_output=False because wizcli outputs errors to stdout.
            for line in stdout:
                self.logger.error(line)
            exit(1)

        stdout_json = None
        for line in stdout:
            try:
                stdout_json = json.loads(line)
                break
            except json.decoder.JSONDecodeError:
                stdout_json = None

        if stdout_json is None:
            self.logger.error("Failed to parse Wiz CLI output as JSON")
            self.logger.debug(stdout)
            exit(1)

        if "result" not in stdout_json or "ruleMatches" not in stdout_json["result"]:
            self.logger.error("Unexpected Wiz CLI output format")
            self.logger.debug(stdout_json)
            exit(1)

        self.add_to_policy_input("wiz", stdout_json)

        if stdout_json["result"]["ruleMatches"] is None:
            self.logger.info("No findings found in the IAC scan.")
        else:
            findings = {}
            # Sort the findings by the severity and their rule id
            for match in stdout_json["result"]["ruleMatches"]:
                if match["severity"] not in findings:
                    findings[match["severity"]] = {}
                if match["rule"]["id"] not in findings[match["severity"]]:
                    findings[match["severity"]][match["rule"]["id"]] = {
                        "rule": match["rule"],
                        "matches": []
                    }
                findings[match["severity"]][match["rule"]["id"]]["matches"].append(match)

            markdown = "# Wiz IAC Scan Findings\n\n"
            markdown += f"**Status:** {stdout_json['status']['state']} **Verdict:** {stdout_json['status']['verdict']}\n"
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
            if "reportUrl" in stdout_json:
                markdown += f"[View Report]({stdout_json['reportUrl']})\n"
            result = self.send_markdown(markdown)
            if not result:
                self.logger.error("Failed to send Wiz CLI output to spacelift")