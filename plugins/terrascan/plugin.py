"""
Terrascan security scanner plugin for Spacelift.

The Terrascan plugin scans your Infrastructure as Code for security and compliance
violations and generates a detailed report with findings categorized by severity.

Supports Terraform, CloudFormation, Kubernetes, and Helm.

You can also access the scan data from a plan policy via the
`input.third_party_metadata.custom.terrascan` object. An example Plan policy is
included with the plugin.

## Usage

1. Install the plugin in your Spacelift account
2. Attach it to your stacks (or use the `autoattach` label)
3. The plugin runs automatically after each plan
4. View results in the Plugins Output tab and/or configure the included policy

## Configuration

The plugin supports these parameters:

- **Additional Arguments**: Pass extra flags to Terrascan

Examples:
- Filter by severity: `--severity HIGH,MEDIUM`
- Skip specific rules: `--skip-rules AC_AWS_0058,AC_AWS_0053`
- Combined: `--severity HIGH --skip-rules AC_AWS_0001`

## Policy Integration

Example policy to block runs with HIGH severity violations:

```rego
package spacelift

import rego.v1

terrascan_data := input.third_party_metadata.custom.terrascan
summary := terrascan_data.summary

deny contains sprintf("Found %d HIGH severity security issues", [summary.high]) if {
    summary.high > 0
}
```

## More Information

- [Terrascan Documentation](https://runterrascan.io/docs/)
- [Terrascan GitHub Repository](https://github.com/tenable/terrascan)
"""

import json
import os

from spaceforge import Binary, Context, Parameter, Policy, SpaceforgePlugin, Variable


class TerrascanPlugin(SpaceforgePlugin):
    __plugin_name__ = "terrascan"
    __version__ = "1.0.1"
    __author__ = "Spacelift"
    __labels__ = ["security", "terraform", "cloudformation", "kubernetes"]

    __binaries__ = [
        Binary(
            name="terrascan",
            download_urls={
                "amd64": "https://github.com/tenable/terrascan/releases/download/v1.19.9/terrascan_1.19.9_Linux_x86_64.tar.gz",
                "arm64": "https://github.com/tenable/terrascan/releases/download/v1.19.9/terrascan_1.19.9_Linux_arm64.tar.gz",
            },
        ),
    ]

    __parameters__ = [
        Parameter(
            name="Additional Arguments",
            id="terrascan_additional_args",
            description="Additional command-line arguments to pass to Terrascan",
            default="",
        ),
    ]

    __contexts__ = [
        Context(
            name_prefix="terrascan",
            description="Terrascan Security Scanner Plugin",
            env=[
                Variable(
                    key="TERRASCAN_ADDITIONAL_ARGS",
                    value_from_parameter="terrascan_additional_args",
                ),
            ],
        )
    ]

    __policies__ = [
        Policy(
            name_prefix="terrascan-enforcement",
            type="PLAN",
            labels=["terrascan", "security"],
            body="""
package spacelift

import rego.v1

# Maximum allowed violations by severity
max_high := 0
max_medium := 5

terrascan_data := input.third_party_metadata.custom.terrascan
violations := terrascan_data.violations
summary := terrascan_data.summary

# Block on HIGH severity violations
deny contains sprintf("Found %d HIGH severity security issues (maximum: %d)", [summary.high, max_high]) if {
    summary.high > max_high
}

# Warn on MEDIUM severity violations
warn contains sprintf("Found %d MEDIUM severity security issues (maximum: %d)", [summary.medium, max_medium]) if {
    summary.medium > max_medium
}
            """,
        )
    ]

    def after_plan(self):
        """Run Terrascan security scan and report findings."""
        try:
            self.logger.info("Starting Terrascan security scan...")

            args = ["scan", "--output", "json"]

            additional_args = os.environ.get("TERRASCAN_ADDITIONAL_ARGS", "").strip()
            if additional_args:
                args.extend(additional_args.split())

            self.logger.info(f"Running: terrascan {' '.join(args)}")
            return_code, stdout, stderr = self.run_cli(
                "terrascan", *args, print_output=False
            )

            if return_code not in [0, 3, 4, 5]:
                self.logger.warning(
                    f"Terrascan returned exit code {return_code}. "
                    "This may indicate scan errors."
                )
                if stderr:
                    self.logger.error("Stderr output: " + "\n".join(stderr))

            try:
                stdout_json = json.loads("\n".join(stdout))
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse Terrascan JSON output: {e}")
                if stdout:
                    self.logger.error(
                        "Raw stdout (first 1000 chars): " + "\n".join(stdout)[:1000]
                    )
                exit(1)

            results = stdout_json.get("results", {})
            violations = results.get("violations", [])
            scan_errors = results.get("scan_errors", [])

            if scan_errors:
                self.logger.debug(
                    f"Terrascan encountered {len(scan_errors)} scan errors "
                    "(this is normal for multi-IaC workspaces):"
                )
                for error in scan_errors[:5]:
                    iac_type = error.get("iac_type", "unknown")
                    directory = error.get("directory", "")
                    err_msg = error.get("errMsg", "")
                    self.logger.debug(f"  {iac_type} in {directory}: {err_msg}")
                if len(scan_errors) > 5:
                    self.logger.debug(f"  ... and {len(scan_errors) - 5} more")

            self.logger.info(f"Terrascan found {len(violations)} violations")

            findings = {"HIGH": [], "MEDIUM": [], "LOW": []}

            for violation in violations:
                severity = violation.get("severity", "UNKNOWN").upper()

                if severity in findings:
                    findings[severity].append(
                        {
                            "rule_id": violation.get("rule_id", ""),
                            "rule_name": violation.get("rule_name", ""),
                            "description": violation.get("description", ""),
                            "severity": severity,
                            "category": violation.get("category", ""),
                            "resource_name": violation.get("resource_name", ""),
                            "resource_type": violation.get("resource_type", ""),
                            "file": violation.get("file", ""),
                            "line": violation.get("line", ""),
                            "module_name": violation.get("module_name", ""),
                        }
                    )

            total_count = sum(len(findings[s]) for s in findings)

            self.add_to_policy_input(
                "terrascan",
                {
                    "violations": violations,
                    "scan_errors": scan_errors,
                    "summary": {
                        "total": total_count,
                        "high": len(findings["HIGH"]),
                        "medium": len(findings["MEDIUM"]),
                        "low": len(findings["LOW"]),
                    },
                },
            )

            if total_count == 0:
                self.logger.info("✓ No security issues found")
                return

            markdown = "# Terrascan Security Scan Results\n\n"
            markdown += f"Found **{total_count}** security issue(s)\n\n"

            severity_emojis = {
                "HIGH": "🔴",
                "MEDIUM": "🟡",
                "LOW": "🟢",
            }

            for severity in ["HIGH", "MEDIUM", "LOW"]:
                issues = findings[severity]
                if len(issues) == 0:
                    continue

                emoji = severity_emojis.get(severity, "")
                plural = "s" if len(issues) > 1 else ""
                markdown += f"## {emoji} {severity} ({len(issues)} finding{plural})\n\n"

                for issue in issues:
                    markdown += f"### {issue['rule_id']}: {issue['rule_name']}\n\n"

                    if issue["resource_name"]:
                        if issue["module_name"]:
                            resource_path = (
                                f"{issue['module_name']}.{issue['resource_type']}."
                                f"{issue['resource_name']}"
                            )
                        else:
                            resource_path = (
                                f"{issue['resource_type']}.{issue['resource_name']}"
                            )
                        markdown += f"**Resource:** `{resource_path}`\n\n"

                    if issue["file"]:
                        file_location = f"**File:** `{issue['file']}`"
                        if issue["line"]:
                            file_location += f" (line {issue['line']})"
                        markdown += f"{file_location}\n\n"

                    if issue["category"]:
                        markdown += f"**Category:** {issue['category']}\n\n"

                    if issue["description"]:
                        markdown += f"**Description:** {issue['description']}\n\n"

                    markdown += "---\n\n"

            result = self.send_markdown(markdown)
            if result:
                self.logger.info(
                    f"Found {total_count} security issues. "
                    "Check Plugins Output tab for details."
                )
            else:
                self.logger.error("Failed to upload plugin outputs")

        except Exception as e:
            self.logger.error(f"Terrascan plugin failed: {e}")
            import traceback

            self.logger.debug(traceback.format_exc())
            exit(1)
