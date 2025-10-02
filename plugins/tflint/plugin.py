import json
import os

from spaceforge import Binary, Context, Parameter, Policy, SpaceforgePlugin, Variable

DEFAULT_TFLINT_CONFIG_FILE = ""
DEFAULT_TFLINT_RECURSIVE = "true"


class TFLintPlugin(SpaceforgePlugin):
    """
    # Plugin TFLint

    The TFLint plugin analyzes your Terraform/OpenTofu files and generates a report with findings categorized by severity.

    You can also access the data from a plan policy via the `input.third_party_metadata.custom.tflint` object.
    An example Plan policy is included with the plugin.

    ## Usage

    1. Install the plugin
    2. Add the `autoattach` label to any stack that uses Terraform/OpenTofu.
    """

    __author__ = "Spacelift"
    __labels__ = ["qa", "security"]
    __plugin_name__ = "tflint"
    __version__ = "0.1.0"

    __binaries__ = [
        Binary(
            name="tflint",
            download_urls={
                "amd64": "https://github.com/terraform-linters/tflint/releases/download/v0.59.1/tflint_linux_amd64.zip",
                "arm64": "https://github.com/terraform-linters/tflint/releases/download/v0.59.1/tflint_linux_arm64.zip",
            },
        ),
    ]

    __parameters__ = [
        Parameter(
            name="Configuration file",
            id="tflint_config_file",
            description="Configuration file name",
            default=DEFAULT_TFLINT_CONFIG_FILE,
        ),
        Parameter(
            name="Recursive",
            id="tflint_recursive",
            description="Run command in each directory recursively. Allowed values: true, false",
            default=DEFAULT_TFLINT_RECURSIVE,
        ),
    ]

    __contexts__ = [
        Context(
            name_prefix="tflint",
            description="TFLint Plugin",
            env=[
                Variable(
                    key="TFLINT_CONFIG_FILE",
                    value_from_parameter="tflint_config_file",
                ),
                Variable(
                    key="TFLINT_RECURSIVE",
                    value_from_parameter="tflint_recursive",
                ),
            ],
        )
    ]

    __policies__ = [
        Policy(
            name_prefix="tflint",
            type="PLAN",
            labels=["tflint"],
            body="""
package spacelift

import rego.v1

max_errors := 0
max_warnings := 0
max_notices := 3

issues := input.third_party_metadata.custom.tflint.issues

deny contains sprintf("Too many errors (%d)", [cnt]) if {
    cnt := count([issue | issue := issues[_]; issue.rule.severity == "error"])
    cnt > max_errors
}

deny contains sprintf("Too many warnings (%d)", [cnt]) if {
    cnt := count([issue | issue := issues[_]; issue.rule.severity == "warning"])
    cnt > max_warnings
}

deny contains sprintf("Too many notices (%d)", [cnt]) if {
    cnt := count([issue | issue := issues[_]; issue.rule.severity == "notice"])
    cnt > max_notices
}
            """,
        )
    ]

    def before_plan(self):
        try:
            options = ["--format=json"]

            # Configuration file
            config_file = (
                os.environ.get("TFLINT_CONFIG_FILE") or DEFAULT_TFLINT_CONFIG_FILE
            )
            if config_file:
                options.append(f"--config={config_file}")

            # Recursive
            recursive = os.environ.get("TFLINT_RECURSIVE") or DEFAULT_TFLINT_RECURSIVE
            if recursive == "true":
                options.append("--recursive")

            return_code, stdout, stderr = self.run_cli("tflint", "--init")
            if return_code != 0:
                self.logger.error(f"tflint --init failed with code {return_code}")
                if stderr:
                    # Display stderr manually because output display is disabled
                    self.logger.error("\n".join(stderr))
                exit(1)

            return_code, stdout, stderr = self.run_cli(
                "tflint", *options, print_output=False
            )
            stdout_json = json.loads("\n".join(stdout))

            # KLUDGE: The `expect_code` argument does not support multiple values so we need to manually handle this.
            # `0` means success and `2` means issues found which is informational, not a failure.
            if return_code not in [0, 2]:
                for error in stdout_json["errors"]:
                    self.logger.error(error["message"])
                exit(1)

            self.add_to_policy_input("tflint", stdout_json)

            if len(stdout_json["issues"]) == 0:
                self.logger.info("No issues found")
                return

            findings = {
                "error": {},
                "warning": {},
                "notice": {},
            }
            for match in stdout_json["issues"]:
                severity = match["rule"]["severity"]
                rule_name = match["rule"]["name"]

                if rule_name not in findings[severity]:
                    findings[severity][rule_name] = []

                findings[severity][rule_name].append(match)

            markdown = "# TFLint Findings\n\n"
            for severity, rules in findings.items():
                # Skip severity level if no issues were found
                if len(rules) == 0:
                    continue

                emoji = None
                if severity == "notice":
                    emoji = "🟡"
                elif severity == "warning":
                    emoji = "🟠"
                elif severity == "error":
                    emoji = "🔴"
                if emoji is not None:
                    markdown += f"## {emoji} {severity.title()} Findings\n\n"
                else:
                    markdown += f"## {severity.title()} Findings\n\n"

                for rule_name, issues in rules.items():
                    markdown += f"### {rule_name}\n\n"
                    for issue in issues:
                        markdown += f"- {issue['message']} _({issue['range']['filename']}:{issue['range']['start']['line']})_\n"
                    markdown += "\n"

            result = self.send_markdown(markdown)
            if result:
                self.logger.info(
                    "Issues found. Check the Plugins Output tab for details."
                )
            else:
                self.logger.error("Failed to upload plugin outputs")
        except Exception as e:
            self.logger.error(f"Plugin failed: {e}")
            exit(1)
