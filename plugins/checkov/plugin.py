"""
Checkov Security Scanner Plugin

This plugin runs Checkov security scanning on Terraform/OpenTofu configurations
during the after_plan hook and reports findings with detailed resource-level
information.

## Features

- Executes Checkov against Terraform/OpenTofu configurations
- Parses and categorizes security findings by severity (when available)
- Generates detailed Markdown reports organized by severity level
- Adds scan results to policy input for OPA policy enforcement
- Supports configurable additional arguments for filtering and customization

## Configuration

### Parameters

- **Additional Arguments**: Optional command-line arguments to pass to Checkov
  (e.g., `--check HIGH,CRITICAL` or `--skip-check CKV_AWS_123`)

### Severity Support

Severity levels (CRITICAL, HIGH, MEDIUM, LOW) are available when using Checkov
with a Bridgecrew/Prisma Cloud API key. To enable severity data:

```
--bc-api-key YOUR_API_KEY
```

Without an API key, the plugin still works but findings are not categorized by
severity in the report.

## Usage

The plugin automatically runs after the plan phase and:

1. Scans your Terraform/OpenTofu code with Checkov
2. Reports failed security checks in a formatted Markdown report
3. Organizes findings by severity level (CRITICAL, HIGH, MEDIUM, LOW) when available
4. Provides check details, resource names, file locations, and remediation links
5. Adds comprehensive scan data to policy input for OPA evaluation

## Example OPA Policy

An example Plan policy is included that denies runs based on severity thresholds.
You can customize the max_critical, max_high, max_medium, and max_low values:

```rego
package spacelift

import rego.v1

# Configure maximum allowed findings by severity
max_critical := 0
max_high := 0
max_medium := 50
max_low := 100

checkov_data := input.third_party_metadata.custom.checkov

deny contains sprintf("Found %d CRITICAL severity Checkov security checks", [checkov_data.summary.critical]) if {
    checkov_data.summary.critical > max_critical
}

deny contains sprintf("Found %d HIGH severity Checkov security checks", [checkov_data.summary.high]) if {
    checkov_data.summary.high > max_high
}
```
"""

import json
import os

from spaceforge import Context, Parameter, Policy, SpaceforgePlugin, Variable

__plugin_name__ = "checkov"
__author__ = "Spacelift"
__version__ = "1.0.1"
__labels__ = ["security", "terraform"]


class CheckovPlugin(SpaceforgePlugin):
    """Checkov security scanner plugin for Spacelift."""

    __parameters__ = [
        Parameter(
            name="Additional Arguments",
            id="checkov_additional_args",
            description="Additional command-line arguments to pass to Checkov (e.g., --check HIGH,CRITICAL or --skip-check CKV_AWS_123)",
            default="",
            required=False,
        )
    ]

    __contexts__ = [
        Context(
            name_prefix="checkov",
            description="Checkov Security Scanner Plugin",
            env=[
                Variable(
                    key="CHECKOV_ADDITIONAL_ARGS",
                    value_from_parameter="checkov_additional_args",
                ),
            ],
        )
    ]

    __policies__ = [
        Policy(
            name_prefix="checkov",
            type="PLAN",
            labels=["checkov"],
            body="""package spacelift

import rego.v1

# Configure maximum allowed findings by severity
max_critical := 0
max_high := 0
max_medium := 50
max_low := 100

checkov_data := input.third_party_metadata.custom.checkov

deny contains sprintf("Found %d CRITICAL severity Checkov security checks", [checkov_data.summary.critical]) if {
    checkov_data.summary.critical > max_critical
}

deny contains sprintf("Found %d HIGH severity Checkov security checks", [checkov_data.summary.high]) if {
    checkov_data.summary.high > max_high
}

deny contains sprintf("Found %d MEDIUM severity Checkov security checks", [checkov_data.summary.medium]) if {
    checkov_data.summary.medium > max_medium
}

deny contains sprintf("Found %d LOW severity Checkov security checks", [checkov_data.summary.low]) if {
    checkov_data.summary.low > max_low
}

# Fallback: deny if total failed checks exceed threshold (for when severity data is not available)
deny contains sprintf("Found %d failed Checkov security checks", [checkov_data.summary.total_failed]) if {
    checkov_data.summary.critical == 0
    checkov_data.summary.high == 0
    checkov_data.summary.medium == 0
    checkov_data.summary.low == 0
    checkov_data.summary.total_failed > max_critical
}
""",
        )
    ]

    def after_plan(self):
        """
        Execute Checkov security scanning after the plan phase.

        This hook runs Checkov against the current directory, parses the JSON
        output, generates a Markdown report for failed checks, and adds
        comprehensive data to the policy input for OPA evaluation.
        """
        try:
            # Build base command arguments
            args = ["--directory", ".", "--output", "json", "--quiet", "--soft-fail"]

            # Append additional arguments from environment variable if provided
            additional_args = os.environ.get("CHECKOV_ADDITIONAL_ARGS", "").strip()
            if additional_args:
                args.extend(additional_args.split())

            # Execute Checkov
            self.logger.info(f"Running Checkov with arguments: {' '.join(args)}")
            return_code, stdout, _ = self.run_cli("checkov", *args, print_output=False)

            # Log any unexpected return codes
            if return_code != 0:
                self.logger.warning(f"Checkov exited with code {return_code}")

            # Parse JSON output with error handling
            try:
                stdout_str = "\n".join(stdout)
                if not stdout_str.strip():
                    self.logger.error("Checkov produced empty output")
                    exit(1)
                stdout_json = json.loads(stdout_str)
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse Checkov JSON output: {e}")
                if stdout:
                    self.logger.error("Raw output: " + "\n".join(stdout))
                exit(1)

            # Process results from all check_type objects
            all_passed_checks = []
            all_failed_checks = []
            all_skipped_checks = []
            check_types = []
            total_resources = 0

            # Checkov returns an array of check_type objects
            if not isinstance(stdout_json, list):
                stdout_json = [stdout_json]

            for result_set in stdout_json:
                check_type = result_set.get("check_type", "unknown")
                check_types.append(check_type)

                results = result_set.get("results", {})
                summary = result_set.get("summary", {})

                # Aggregate checks
                passed_checks = results.get("passed_checks", [])
                failed_checks = results.get("failed_checks", [])
                skipped_checks = results.get("skipped_checks", [])

                all_passed_checks.extend(passed_checks)
                all_failed_checks.extend(failed_checks)
                all_skipped_checks.extend(skipped_checks)

                # Aggregate summary stats
                total_resources += summary.get("resource_count", 0)

            # Build policy input data structure with severity summary
            severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for check in all_failed_checks:
                severity = check.get("severity")
                if severity and severity in severity_counts:
                    severity_counts[severity] += 1

            policy_data = {
                "summary": {
                    "total_passed": len(all_passed_checks),
                    "total_failed": len(all_failed_checks),
                    "total_skipped": len(all_skipped_checks),
                    "resource_count": total_resources,
                    "critical": severity_counts["CRITICAL"],
                    "high": severity_counts["HIGH"],
                    "medium": severity_counts["MEDIUM"],
                    "low": severity_counts["LOW"],
                },
                "failed_checks": all_failed_checks,
                "passed_checks": all_passed_checks,
                "check_types": check_types,
            }
            self.add_to_policy_input("checkov", policy_data)

            # If no failed checks found, log success and return early
            if len(all_failed_checks) == 0:
                self.logger.info("✓ No security issues found")
                return

            # Categorize findings by severity
            findings_by_severity = {
                "CRITICAL": [],
                "HIGH": [],
                "MEDIUM": [],
                "LOW": [],
                "UNKNOWN": [],
            }
            has_severity_data = False

            for check in all_failed_checks:
                severity = check.get("severity")
                if severity and severity in findings_by_severity:
                    findings_by_severity[severity].append(check)
                    has_severity_data = True
                else:
                    # If severity is null or unknown, put in UNKNOWN category
                    findings_by_severity["UNKNOWN"].append(check)

            # Generate Markdown report for failed checks
            markdown = "# Checkov Security Scan Results\n\n"
            markdown += f"Found **{len(all_failed_checks)}** failed check(s) across **{total_resources}** resources\n\n"

            severity_emojis = {
                "CRITICAL": "🔴",
                "HIGH": "🟠",
                "MEDIUM": "🟡",
                "LOW": "🟢",
            }

            def format_check(check):
                """Helper function to format a single check in markdown"""
                check_id = check.get("check_id", "N/A")
                check_name = check.get("check_name", "Unknown check")
                resource = check.get("resource", "N/A")
                file_path = check.get("file_path", "N/A")
                file_line_range = check.get("file_line_range", [])
                bc_check_id = check.get("bc_check_id", "N/A")
                guideline = check.get("guideline")

                output = f"### {check_id}: {check_name}\n\n"

                # Format line range
                if file_line_range and len(file_line_range) == 2:
                    line_info = f"at line {file_line_range[0]}-{file_line_range[1]}"
                else:
                    line_info = ""

                output += (
                    f"**Resource:** `{resource}` (in `{file_path}` {line_info})\n\n"
                )
                output += f"**Check ID:** {check_id} ({bc_check_id})\n\n"

                if guideline:
                    output += f"[More information]({guideline})\n\n"

                output += "---\n\n"
                return output

            # If we have severity data, organize by severity
            if has_severity_data:
                for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
                    checks = findings_by_severity[severity]
                    if len(checks) == 0:
                        continue

                    emoji = severity_emojis.get(severity, "")
                    markdown += f"## {emoji} {severity} ({len(checks)} finding{'s' if len(checks) > 1 else ''})\n\n"

                    for check in checks:
                        markdown += format_check(check)

                # Add UNKNOWN section if there are checks without severity
                unknown_checks = findings_by_severity["UNKNOWN"]
                if len(unknown_checks) > 0:
                    markdown += f"## Failed Checks ({len(unknown_checks)} finding{'s' if len(unknown_checks) > 1 else ''})\n\n"
                    for check in unknown_checks:
                        markdown += format_check(check)
            else:
                # No severity data available, show all checks in one section
                markdown += f"## Failed Checks ({len(all_failed_checks)} findings)\n\n"
                for check in all_failed_checks:
                    markdown += format_check(check)

            # Send markdown report
            self.send_markdown(markdown)

            # Log summary message
            self.logger.info(
                f"Found {len(all_failed_checks)} security issues. Check the Plugins Output tab for details."
            )

        except Exception as e:
            self.logger.error(f"Plugin failed: {e}")
            exit(1)
