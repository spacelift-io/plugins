import json
import os

from spaceforge import Binary, Context, Parameter, SpaceforgePlugin, Variable


class TruffleHogPlugin(SpaceforgePlugin):
    """
    TruffleHog Secret Scanner Plugin

    This plugin runs TruffleHog secret scanning on the filesystem during the
    before_plan hook and reports findings organized by verification status.

    ## Features

    - Scans filesystem for 800+ types of secrets including AWS keys, API tokens,
      and database credentials
    - Detects and reports both verified (confirmed active) and unverified secrets
    - Generates detailed Markdown reports organized by verification status
    - Reports file locations and line numbers for each finding
    - Includes rotation guide URLs for remediation
    - Fails the run when secrets are detected
    - Never logs or displays actual secret values

    ## Configuration

    ### Parameters

    - **Results Filter**: Controls which finding types to report. Options include:
      - `verified` - Only confirmed active secrets
      - `unknown` - Only unverified patterns
      - `verified,unknown` - Both types (default)

    - **Additional Arguments**: Optional command-line arguments to pass to TruffleHog
      for advanced customization

    ## Usage

    The plugin automatically runs before the plan phase and:

    1. Scans your filesystem with TruffleHog
    2. Reports verified secrets and unverified patterns
    3. Organizes findings by verification status
    4. Provides detector descriptions, file locations, and rotation guides
    5. Fails the run when secrets are detected

    ## Security Note

    This plugin NEVER logs or displays actual secret values. Only metadata about detected
    secrets is reported.
    """

    __plugin_name__ = "trufflehog"
    __author__ = "Spacelift"
    __version__ = "1.0.1"
    __labels__ = ["security", "secrets"]

    __parameters__ = [
        Parameter(
            name="Results Filter",
            id="results_filter",
            description='Controls which finding types to report (e.g., "verified", "unknown", or "verified,unknown")',
            default="verified,unknown",
            required=False,
        ),
        Parameter(
            name="Additional Arguments",
            id="additional_args",
            description="Additional command-line arguments to pass to TruffleHog",
            default="",
            required=False,
        ),
    ]

    __binaries__ = [
        Binary(
            name="trufflehog",
            download_urls={
                "amd64": "https://github.com/trufflesecurity/trufflehog/releases/download/v3.90.12/trufflehog_3.90.12_linux_amd64.tar.gz",
                "arm64": "https://github.com/trufflesecurity/trufflehog/releases/download/v3.90.12/trufflehog_3.90.12_linux_arm64.tar.gz",
            },
        )
    ]

    __contexts__ = [
        Context(
            name_prefix="trufflehog",
            description="TruffleHog Secret Scanner Plugin",
            env=[
                Variable(
                    key="TRUFFLEHOG_RESULTS_FILTER",
                    value_from_parameter="results_filter",
                ),
                Variable(
                    key="TRUFFLEHOG_ADDITIONAL_ARGS",
                    value_from_parameter="additional_args",
                ),
            ],
        )
    ]

    def before_plan(self):
        """
        Execute TruffleHog secret scanning before the plan phase.

        This hook runs TruffleHog against the filesystem, parses the JSON
        output, generates a Markdown report for findings organized by
        verification status, and fails the run when secrets are detected.
        """
        try:
            # Build command arguments
            results_filter = os.environ.get(
                "TRUFFLEHOG_RESULTS_FILTER", "verified,unknown"
            )
            additional_args_str = os.environ.get(
                "TRUFFLEHOG_ADDITIONAL_ARGS", ""
            ).strip()

            args = ["filesystem", ".", "--json", "--results", results_filter]

            # Append additional arguments if provided
            if additional_args_str:
                args.extend(additional_args_str.split())

            # Execute TruffleHog
            self.logger.info(f"Running TruffleHog with arguments: {' '.join(args)}")
            return_code, stdout, stderr = self.run_cli(
                "trufflehog", *args, print_output=False
            )

            # TruffleHog exit codes:
            # 0 = no secrets found
            # 183 = secrets found
            # other = error
            if return_code not in [0, 183]:
                self.logger.error(
                    f"TruffleHog failed with exit code {return_code}: {' '.join(stderr)}"
                )
                exit(1)

            # Parse newline-delimited JSON output
            findings = []
            for line in stdout:
                line = line.strip()
                if not line:
                    continue

                try:
                    finding = json.loads(line)
                    findings.append(finding)
                except json.JSONDecodeError as e:
                    self.logger.warning(f"Failed to parse JSON line: {e}")
                    continue

            # Filter out log messages and findings from .terraform/ folders
            filtered_findings = []
            for finding in findings:
                # Skip if not a finding (e.g., log messages, status updates)
                if "SourceMetadata" not in finding:
                    continue

                source_metadata = finding.get("SourceMetadata", {})
                data = source_metadata.get("Data", {})
                filesystem = data.get("Filesystem", {})
                file_path = filesystem.get("file", "")

                # Skip findings in .terraform/ directories
                if ".terraform/" in file_path:
                    continue

                filtered_findings.append(finding)

            # Categorize findings by verification status
            verified_secrets = []
            unverified_secrets = []

            for finding in filtered_findings:
                if finding.get("Verified", False):
                    verified_secrets.append(finding)
                else:
                    unverified_secrets.append(finding)

            # Sort findings by file path, then line number
            def sort_key(finding):
                source_metadata = finding.get("SourceMetadata", {})
                data = source_metadata.get("Data", {})
                filesystem = data.get("Filesystem", {})
                file_path = filesystem.get("file", "")
                line_number = filesystem.get("line", 0)
                return (file_path, line_number)

            verified_secrets.sort(key=sort_key)
            unverified_secrets.sort(key=sort_key)

            total_findings = len(filtered_findings)
            verified_count = len(verified_secrets)
            unverified_count = len(unverified_secrets)

            # If no findings, log success and return
            if total_findings == 0:
                self.logger.info("No secrets found")
                return

            # Generate Markdown report
            markdown = "# TruffleHog Secret Scan Results\n\n"
            markdown += f"Found **{total_findings}** potential secret(s): "
            markdown += (
                f"**{verified_count}** verified, **{unverified_count}** unverified\n\n"
            )

            # Section 1: Verified Secrets
            if verified_count > 0:
                markdown += f"## 🔴 VERIFIED SECRETS ({verified_count} finding{'s' if verified_count > 1 else ''})\n\n"
                markdown += "These secrets have been confirmed as active and should be rotated immediately.\n\n"

                for secret in verified_secrets:
                    detector_name = secret.get("DetectorName", "Unknown")
                    detector_desc = secret.get("DetectorDescription", "")

                    # Extract source metadata
                    source_metadata = secret.get("SourceMetadata", {})
                    data = source_metadata.get("Data", {})
                    filesystem = data.get("Filesystem", {})
                    file_path = filesystem.get("file", "N/A")
                    line_number = filesystem.get("line", "N/A")

                    # Extract extra data (rotation guide, etc.)
                    extra_data = secret.get("ExtraData", {})
                    rotation_guide = extra_data.get("rotation_guide", "")

                    markdown += f"### {detector_name}\n\n"
                    if detector_desc:
                        markdown += f"{detector_desc}\n\n"
                    markdown += f"**Location:** `{file_path}` at line {line_number}\n\n"
                    markdown += "**Status:** ✅ Verified (confirmed active)\n\n"

                    if rotation_guide:
                        markdown += f"**Rotation Guide:** {rotation_guide}\n\n"

                    markdown += "---\n\n"

            # Section 2: Unverified Patterns
            if unverified_count > 0:
                markdown += f"## 🟡 UNVERIFIED PATTERNS ({unverified_count} finding{'s' if unverified_count > 1 else ''})\n\n"
                markdown += "These patterns match secret formats but could not be verified. Review and rotate if legitimate.\n\n"

                for secret in unverified_secrets:
                    detector_name = secret.get("DetectorName", "Unknown")
                    detector_desc = secret.get("DetectorDescription", "")

                    # Extract source metadata
                    source_metadata = secret.get("SourceMetadata", {})
                    data = source_metadata.get("Data", {})
                    filesystem = data.get("Filesystem", {})
                    file_path = filesystem.get("file", "N/A")
                    line_number = filesystem.get("line", "N/A")

                    # Verification error
                    verification_error = secret.get("VerificationError", "")

                    markdown += f"### {detector_name}\n\n"
                    if detector_desc:
                        markdown += f"{detector_desc}\n\n"
                    markdown += f"**Location:** `{file_path}` at line {line_number}\n\n"
                    markdown += "**Status:** ⚠️ Unverified\n\n"

                    if verification_error:
                        markdown += f"**Verification Note:** {verification_error}\n\n"

                    markdown += "---\n\n"

            # Send markdown report
            self.send_markdown(markdown)

            # Log summary
            self.logger.info(
                "Security issues found. Check the Plugins Output tab for details."
            )

            # Fail the run
            exit(1)

        except Exception as e:
            self.logger.error(f"Plugin failed: {e}")
            exit(1)
