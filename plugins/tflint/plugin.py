import json
import os

from spaceforge import Binary, Context, Parameter, Policy, SpaceforgePlugin, Variable


class TFLintPlugin(SpaceforgePlugin):
    """
    A plugin for running TFLint on Terraform/OpenTofu configurations.
    """

    __author__ = "Liferay"
    __labels__ = ["linting", "terraform"]
    __plugin_name__ = "TFLint"
    __version__ = "1.1.0"

    __binaries__ = [
        Binary(
            name="tflint",
            download_urls={
                "amd64": "https://github.com/terraform-linters/tflint/releases/download/v0.55.1/tflint_linux_amd64.zip",
                "arm64": "https://github.com/terraform-linters/tflint/releases/download/v0.55.1/tflint_linux_arm64.zip",
            },
        ),
    ]

    __parameters__ = [
        Parameter(
            name="Additional Arguments",
            id="tflint_additional_args",
            description="Additional command-line arguments to pass to TFLint",
            default="",
            type="string",
            required=False,
        ),
    ]

    __contexts__ = [
        Context(
            name_prefix="TFLINT",
            description="TFLint Plugin",
            env=[
                Variable(
                    key="TFLINT_ADDITIONAL_ARGS",
                    value_from_parameter="Additional Arguments",
                ),
            ],
        )
    ]

    __policies__ = [
        Policy(
            name_prefix="TFLINT",
            type="PLAN",
            engine_type="REGO_V0",
            body="""
package spacelift

# Deny the run if any TFLint issues are found
deny[msg] {
	payload := get_metadata("tflint")
	issue := payload.issues[_]
	msg := sprintf("🔍 TFLint finding: \"%s\" in \"%s:%d\".", [issue.message, issue.range.filename, issue.range.start.line])
}

# Helpers
get_metadata(name) := val if {
	val := input.third_party_metadata.custom[name]
} else := val if {
	val := input.third_party_metadata[name]
}
""",
        )
    ]

    def after_plan(self):
        try:
            # 1. Initialize TFLint
            self.logger.info("Initializing TFLint...")
            self.run_cli("tflint", "--init", print_output=False)

            # 2. Run ASCII scan for logs
            # This provides the human-readable output the user likes to see in logs
            self.logger.info("--- TFLint Analysis (ASCII) ---")
            additional_args = os.environ.get("TFLINT_ADDITIONAL_ARGS", "").strip()
            args = additional_args.split() if additional_args else []
            self.run_cli("tflint", *args, print_output=True)

            # 3. Generate JSON for policy input
            self.logger.info("Generating TFLint JSON metadata...")
            json_args = ["--format", "json"]
            if additional_args:
                json_args.extend(additional_args.split())

            return_code, stdout, stderr = self.run_cli(
                "tflint", *json_args, print_output=False
            )

            # Parse JSON output
            try:
                content = "\n".join(stdout)
                if not content.strip():
                    stdout_json = {"issues": []}
                else:
                    data = json.loads(content)
                    # TFLint sometimes returns a list of issues directly
                    if isinstance(data, list):
                        stdout_json = {"issues": data}
                    else:
                        stdout_json = data
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse TFLint JSON output: {e}")
                exit(1)

            # Add to policy input
            self.add_to_policy_input("tflint", stdout_json)

            issues = stdout_json.get("issues", [])
            if not issues:
                self.logger.info("✓ No TFLint issues found.")
                return

            # 4. Generate Markdown report for Plugins Output tab
            markdown = "# TFLint Analysis Summary\n\n"
            markdown += f"Found **{len(issues)}** issue(s).\n\n"

            # Group issues by severity
            issues_by_severity = {"error": [], "warning": [], "notice": []}
            severity_emojis = {"error": "🔴", "warning": "🟡", "notice": "🔵"}

            for issue in issues:
                severity = issue.get("rule", {}).get("severity", "notice").lower()
                if severity in issues_by_severity:
                    issues_by_severity[severity].append(issue)
                else:
                    issues_by_severity["notice"].append(issue)

            for severity in ["error", "warning", "notice"]:
                findings = issues_by_severity[severity]
                if not findings:
                    continue

                emoji = severity_emojis.get(severity, "ℹ️")
                markdown += f"## {emoji} {severity.upper()} ({len(findings)})\n\n"

                for issue in findings:
                    rule = issue.get("rule", {}).get("name", "unknown")
                    msg = issue.get("message", "No message.")
                    file = issue.get("range", {}).get("filename", "unknown")
                    line = issue.get("range", {}).get("start", {}).get("line", 0)
                    link = issue.get("rule", {}).get("link", "")

                    markdown += f"### {rule}\n"
                    markdown += f"**Location:** `{file}:{line}`\n\n"
                    markdown += f"{msg}\n\n"
                    if link:
                        markdown += f"[View documentation]({link})\n\n"
                    markdown += "---\n\n"

            # Upload markdown report
            if self.send_markdown(markdown):
                self.logger.info(f"TFLint report ({len(issues)} findings) uploaded to UI.")
            else:
                self.logger.error("Failed to upload TFLint report to UI.")

        except Exception as e:
            self.logger.error(f"TFLint plugin failed: {e}")
            exit(1)
