import json
import os

from spaceforge import Binary, Context, Parameter, Policy, SpaceforgePlugin, Variable

# tfcov lives at https://github.com/spacelift-solutions/tfcov; the framework's
# installer downloads and extracts its release archives at runtime. Pinned to a
# tag so a tfcov release never silently changes installed plugins — bump
# deliberately and regenerate plugin.yaml.
_TFCOV_VERSION = "0.0.1"
_DIST = (
    f"https://github.com/spacelift-solutions/tfcov/releases/download/v{_TFCOV_VERSION}"
)


class CoveragePlugin(SpaceforgePlugin):
    """
    Gates Terraform/OpenTofu module PRs on test coverage.

    Spacelift module tests instantiate a module through the `project_root` of each test case in
    `.spacelift/config.yml` and apply it. This plugin measures how much of the module's surface
    those examples exercise — its input variables and its count/for_each/dynamic/conditional
    branch points — and denies the run when coverage falls below a threshold (absolute mode) or
    below the base branch's coverage (ratchet mode).

    The `tfcov` binary discovers the module and its examples from `.spacelift/config.yml`, so a
    single instance of this plugin can be autoattached to any number of modules. Its report is
    exposed to policies via `input.third_party_metadata.custom.coverage`.
    """

    __plugin_name__ = "Module Test Coverage"
    __labels__ = ["testing", "terraform", "opentofu", "modules"]
    __version__ = "1.0.0"
    __author__ = "Spacelift Team"

    __binaries__ = [
        Binary(
            name="tfcov",
            download_urls={
                "amd64": f"{_DIST}/tfcov_linux_amd64.tar.gz",
                "arm64": f"{_DIST}/tfcov_linux_arm64.tar.gz",
            },
        )
    ]

    __parameters__ = [
        Parameter(
            name="Mode",
            id="mode",
            description="'absolute' fails below the fixed thresholds; 'ratchet' fails when coverage drops below the base ref.",
            type="string",
            default="absolute",
            required=False,
        ),
        Parameter(
            name="Minimum Variable Coverage",
            id="min_variable_coverage",
            description="Absolute mode: the minimum percentage of input variables exercised by the examples.",
            type="number",
            default=80,
            required=False,
        ),
        Parameter(
            name="Minimum Branch Coverage",
            id="min_branch_coverage",
            description="Absolute mode: the minimum percentage of assessable branch points exercised both ways.",
            type="number",
            default=70,
            required=False,
        ),
        Parameter(
            name="Fail On",
            id="fail_on",
            description="'block' denies the run; 'warn' only reports.",
            type="string",
            default="warn",
            required=False,
        ),
        Parameter(
            name="Base Ref",
            id="base_ref",
            description="Ratchet mode: git ref to compare against. Leave empty to auto-detect (the module's tracked branch, then the previous commit). Requires fetchable git history.",
            type="string",
            default="",
            required=False,
        ),
    ]

    __contexts__ = [
        Context(
            name_prefix="TFCOV",
            description="Module Test Coverage Plugin",
            env=[
                Variable(key="TFCOV_MODE", value_from_parameter="mode"),
                Variable(
                    key="TFCOV_MIN_VARIABLE_COVERAGE",
                    value_from_parameter="min_variable_coverage",
                ),
                Variable(
                    key="TFCOV_MIN_BRANCH_COVERAGE",
                    value_from_parameter="min_branch_coverage",
                ),
                Variable(key="TFCOV_FAIL_ON", value_from_parameter="fail_on"),
                Variable(key="TFCOV_BASE_REF", value_from_parameter="base_ref"),
            ],
        )
    ]

    __policies__ = [
        Policy(
            name_prefix="module_coverage",
            type="PLAN",
            engine_type="REGO_V1",
            body="""
package spacelift

sample := true

cov := input.third_party_metadata.custom.coverage

deny contains msg if {
    cov.config.fail_on == "block"
    some msg in failure
}

warn contains msg if {
    cov.config.fail_on == "warn"
    some msg in failure
}

failure contains msg if {
    cov.config.mode == "absolute"
    cov.report.variable_coverage < cov.config.min_variable_coverage
    msg := sprintf("Variable coverage %v%% is below the required %v%%", [cov.report.variable_coverage, cov.config.min_variable_coverage])
}

failure contains msg if {
    cov.config.mode == "absolute"
    cov.report.branch_coverage < cov.config.min_branch_coverage
    msg := sprintf("Branch coverage %v%% is below the required %v%%", [cov.report.branch_coverage, cov.config.min_branch_coverage])
}

failure contains msg if {
    cov.config.mode == "ratchet"
    cov.report.variable_coverage < cov.report.base.variable_coverage
    msg := sprintf("Variable coverage dropped from %v%% to %v%%", [cov.report.base.variable_coverage, cov.report.variable_coverage])
}

failure contains msg if {
    cov.config.mode == "ratchet"
    cov.report.branch_coverage < cov.report.base.branch_coverage
    msg := sprintf("Branch coverage dropped from %v%% to %v%%", [cov.report.base.branch_coverage, cov.report.branch_coverage])
}
""",
            labels=["coverage-plugin"],
        )
    ]

    def _resolve_base_ref(self):
        """Ratchet base: an explicit ref wins; otherwise the module's tracked
        branch, falling back to the previous commit."""
        base_ref = os.environ.get("TFCOV_BASE_REF", "").strip()
        if base_ref:
            return base_ref
        tracked = os.environ.get("TF_VAR_spacelift_stack_branch", "").strip()
        if tracked:
            return f"origin/{tracked}"
        return "HEAD^"

    def after_init(self):
        mode = os.environ.get("TFCOV_MODE", "absolute")

        args = [
            "tfcov",
            "--spacelift",
            "--format",
            "json",
            "--markdown-out",
            "tfcov.md",
        ]
        if mode == "ratchet":
            args += ["--base-ref", self._resolve_base_ref()]

        return_code, stdout, stderr = self.run_cli(*args, print_output=False)
        if return_code != 0:
            for line in stderr:
                self.logger.error(line)
            exit(1)

        report = json.loads("\n".join(stdout))
        self._write_policy_inputs(report, mode)

        if os.path.exists("tfcov.md"):
            with open("tfcov.md") as f:
                self.send_markdown(f.read())

    def _write_policy_inputs(self, report, mode):
        """Write the coverage policy input where Spacelift will find it.

        Spacelift scans each test case's project_root for *.custom.spacelift.json,
        but module test runs don't set TF_VAR_spacelift_project_root, so the run
        wrapper leaves us in the repo root. Every test case's project_root is one
        of report["examples"], so write the input into each — whichever is the
        current run's project_root gets picked up."""
        payload = json.dumps(
            {
                "report": report,
                "config": {
                    "mode": mode,
                    "fail_on": os.environ.get("TFCOV_FAIL_ON", "warn"),
                    "min_variable_coverage": float(
                        os.environ.get("TFCOV_MIN_VARIABLE_COVERAGE", "80")
                    ),
                    "min_branch_coverage": float(
                        os.environ.get("TFCOV_MIN_BRANCH_COVERAGE", "70")
                    ),
                },
            }
        )
        module_root = report.get("module_root") or "."
        targets = report.get("examples") or ["."]
        for example in targets:
            path = os.path.join(module_root, example, "coverage.custom.spacelift.json")
            try:
                with open(path, "w") as f:
                    f.write(payload)
            except OSError as e:
                self.logger.warning(f"could not write policy input to {path}: {e}")
