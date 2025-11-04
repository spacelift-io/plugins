import json
import os

from spaceforge import Binary, Context, Parameter, Policy, SpaceforgePlugin, Variable


class TrivyPlugin(SpaceforgePlugin):
    """
    # Plugin Trivy

    The Trivy plugin scans your Terraform/OpenTofu configurations for security misconfigurations
    and generates a detailed report with findings categorized by severity.

    You can also access the scan data from a plan policy via the
    `input.third_party_metadata.custom.trivy` object. An example Plan policy is
    included with the plugin.

    ## Usage

    1. Install the plugin in your Spacelift account
    2. Attach it to stacks using Terraform/OpenTofu (or use the `autoattach` label)
    3. The plugin runs automatically after each plan
    4. View results in the Plugins Output tab and/or configure the included policy

    ## Configuration

    Use the "Additional Arguments" parameter to pass extra flags to Trivy, for example:
    - `--severity CRITICAL,HIGH` to scan only critical and high severity issues
    - `--skip-dirs tests` to exclude specific directories
    """

    __author__ = "Spacelift"
    __labels__ = ["security", "terraform"]
    __plugin_name__ = "trivy"
    __version__ = "1.0.1"

    __binaries__ = [
        Binary(
            name="trivy",
            download_urls={
                "amd64": "https://github.com/aquasecurity/trivy/releases/download/v0.67.2/trivy_0.67.2_Linux-64bit.tar.gz",
                "arm64": "https://github.com/aquasecurity/trivy/releases/download/v0.67.2/trivy_0.67.2_Linux-ARM64.tar.gz",
            },
        ),
    ]

    __parameters__ = [
        Parameter(
            name="Additional Arguments",
            id="trivy_additional_args",
            description="Additional command-line arguments to pass to Trivy",
            default="",
        ),
    ]

    __contexts__ = [
        Context(
            name_prefix="trivy",
            description="Trivy Plugin",
            env=[
                Variable(
                    key="TRIVY_ADDITIONAL_ARGS",
                    value_from_parameter="trivy_additional_args",
                ),
            ],
        )
    ]

    __policies__ = [
        Policy(
            name_prefix="trivy",
            type="PLAN",
            labels=["trivy"],
            body="""
package spacelift

import rego.v1

max_critical := 0
max_high := 0

trivy_results := input.third_party_metadata.custom.trivy.Results

misconfigs := [m | some result in trivy_results; m := result.Misconfigurations[_]]

deny contains sprintf("Found %d critical security issues", [cnt]) if {
    cnt := count([m | m := misconfigs[_]; m.Severity == "CRITICAL"])
    cnt > max_critical
}

deny contains sprintf("Found %d high security issues", [cnt]) if {
    cnt := count([m | m := misconfigs[_]; m.Severity == "HIGH"])
    cnt > max_high
}
            """,
        )
    ]

    def after_plan(self):
        try:
            # Build Trivy command
            args = ["config", "--format", "json", "--quiet"]

            # Add additional arguments if provided
            additional_args = os.environ.get("TRIVY_ADDITIONAL_ARGS", "").strip()
            if additional_args:
                args.extend(additional_args.split())

            # Execute Trivy scan
            return_code, stdout, stderr = self.run_cli(
                "trivy", *args, ".", print_output=False
            )

            # Parse JSON output
            try:
                stdout_json = json.loads("\n".join(stdout))
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse Trivy JSON output: {e}")
                if stdout:
                    self.logger.error("Raw output: " + "\n".join(stdout))
                exit(1)

            # Add to policy input
            self.add_to_policy_input("trivy", stdout_json)

            # Extract results and categorize findings
            results = stdout_json.get("Results", [])

            findings = {"CRITICAL": [], "HIGH": [], "MEDIUM": [], "LOW": []}

            total_count = 0
            for result in results:
                misconfigurations = result.get("Misconfigurations", [])
                for misconfig in misconfigurations:
                    severity = misconfig.get("Severity", "UNKNOWN")
                    if severity in findings:
                        findings[severity].append(
                            {
                                "id": misconfig.get("ID", ""),
                                "avdid": misconfig.get("AVDID", ""),
                                "title": misconfig.get("Title", ""),
                                "description": misconfig.get("Description", ""),
                                "message": misconfig.get("Message", ""),
                                "severity": severity,
                                "resolution": misconfig.get("Resolution", ""),
                                "primary_url": misconfig.get("PrimaryURL", ""),
                                "resource": misconfig.get("CauseMetadata", {}).get(
                                    "Resource", ""
                                ),
                                "start_line": misconfig.get("CauseMetadata", {}).get(
                                    "StartLine", ""
                                ),
                                "end_line": misconfig.get("CauseMetadata", {}).get(
                                    "EndLine", ""
                                ),
                            }
                        )
                        total_count += 1

            # If no findings, report success
            if total_count == 0:
                self.logger.info("✓ No security issues found")
                return

            # Generate markdown report
            markdown = "# Trivy Security Scan Results\n\n"
            markdown += f"Found **{total_count}** security issue(s)\n\n"

            severity_emojis = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢",
            }

            for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                issues = findings[severity]
                if len(issues) == 0:
                    continue

                emoji = severity_emojis.get(severity, "")
                markdown += f"## {emoji} {severity} ({len(issues)} finding{'s' if len(issues) > 1 else ''})\n\n"

                for issue in issues:
                    # Use AVDID if available, otherwise use ID
                    issue_id = issue["avdid"] if issue["avdid"] else issue["id"]
                    markdown += f"### {issue_id}: {issue['title']}\n\n"

                    if issue["resource"]:
                        location = f"**Resource:** `{issue['resource']}`"
                        if issue["start_line"]:
                            location += f" (line {issue['start_line']}"
                            if (
                                issue["end_line"]
                                and issue["end_line"] != issue["start_line"]
                            ):
                                location += f"-{issue['end_line']}"
                            location += ")"
                        markdown += f"{location}\n\n"

                    if issue["message"]:
                        markdown += f"**Issue:** {issue['message']}\n\n"
                    elif issue["description"]:
                        markdown += f"**Issue:** {issue['description']}\n\n"

                    if issue["resolution"]:
                        markdown += f"**Resolution:** {issue['resolution']}\n\n"

                    if issue["primary_url"]:
                        markdown += f"[More information]({issue['primary_url']})\n\n"

                    markdown += "---\n\n"

            # Send markdown report
            result = self.send_markdown(markdown)
            if result:
                self.logger.info(
                    "Security issues found. Check the Plugins Output tab for details."
                )
            else:
                self.logger.error("Failed to upload plugin outputs")
        except Exception as e:
            self.logger.error(f"Plugin failed: {e}")
            exit(1)
