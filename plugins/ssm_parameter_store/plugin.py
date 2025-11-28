import os
from typing import List, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from spaceforge import Context, Parameter, SpaceforgePlugin, Variable


class SSMParameterStorePlugin(SpaceforgePlugin):
    """
    # Plugin SSM Parameter Store

    This plugin fetches secrets from AWS Systems Manager Parameter Store based on stack labels and makes them available as environment variables.

    ## Usage

    1. Add labels to your Spacelift stacks with the format `secret:/path/to/parameter`
    2. Attach this plugin to stacks with your stack label
    3. Label your stack with the `secret:` prefix followed by the SSM parameter path
    3. The plugin will fetch the parameters from SSM and make them available as environment variables for all subsequent phases.

    ## Label Format

    Stack labels should follow this pattern:
    - `secret:/path/to/parameter` - The parameter path in AWS SSM Parameter Store

    You can add multiple `secret:` labels to a single stack to fetch multiple parameters.

    ## Environment Variables

    The fetched secrets will be available as environment variables with the following naming:
    - Path `/path/to/parameter` becomes `TF_VAR_SSM_PATH_TO_PARAMETER`
    - Special characters are replaced with underscores
    - All letters are uppercased

    ## Examples

    If your stack has the label `secret:/prod/db/password`, the plugin will:
    1. Fetch the parameter from AWS SSM at path `/prod/db/password`
    2. Make it available as environment variable `TF_VAR_SSM_PROD_DB_PASSWORD`

    Multiple secrets example:
    - Label: `secret:/prod/api/key` → Env var: `TF_VAR_SSM_PROD_API_KEY`
    - Label: `secret:/prod/db-connection-string` → Env var: `TF_VAR_SSM_PROD_DB_CONNECTION_STRING`

    ## AWS Credentials

    This plugin uses boto3 and requires AWS credentials to be configured in your Spacelift stack.
    You can use:
    - AWS integration (recommended)
    - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    - IAM roles

    ## Configuration

    You can optionally configure the AWS region using the `aws_region` parameter.
    If not specified, it will use the default region from your AWS configuration.

    ## Security

    Secrets are written to a temporary shell script (/tmp/ssm_exports.sh) with restrictive permissions (0600).
    The script is sourced by hooks to export environment variables. The file is automatically cleaned up after the run.
    """

    # Plugin metadata
    __plugin_name__ = "SSM Parameter Store"
    __labels__ = ["secrets management", "aws", "ssm", "autoattach"]
    __version__ = "1.0.0"
    __author__ = "Spacelift Team"

    # Plugin parameters
    __parameters__ = [
        Parameter(
            name="AWS Region",
            id="aws_region",
            description="AWS region for SSM Parameter Store. If not specified, uses the default region from AWS configuration.",
            sensitive=False,
            required=False,
            default="us-east-1",
            type="string",
        )
    ]

    # Plugin contexts
    __contexts__ = [
        Context(
            priority=0,
            name_prefix="get-ssm-parameters",
            description="Get SSM parameters from AWS Systems Manager Parameter Store",
            env=[
                Variable(
                    key="AWS_DEFAULT_REGION",
                    value_from_parameter="aws_region",
                    sensitive=False,
                )
            ],
        ),
        Context(
            priority=1,
            name_prefix="set-ssm-parameters",
            description="Sets SSM Parameter Store parameters as environment variables",
            hooks={
                "before_init": [
                    "[ -f /tmp/ssm_exports.sh ] && . /tmp/ssm_exports.sh || true"
                ],
                "before_plan": [
                    "[ -f /tmp/ssm_exports.sh ] && . /tmp/ssm_exports.sh || true"
                ],
                "before_apply": [
                    "[ -f /tmp/ssm_exports.sh ] && . /tmp/ssm_exports.sh || true"
                ],
                "before_perform": [
                    "[ -f /tmp/ssm_exports.sh ] && . /tmp/ssm_exports.sh || true"
                ],
            },
        ),
    ]

    def __init__(self):
        super().__init__()
        self.aws_region = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

    def _parse_labels(self) -> List[str]:
        """Parse stack labels and extract SSM parameter paths."""
        labels_str = os.environ.get("TF_VAR_spacelift_stack_labels", "")
        if not labels_str:
            self.logger.info("No stack labels found in TF_VAR_spacelift_stack_labels")
            return []

        labels = [label.strip() for label in labels_str.split(",")]
        self.logger.debug(f"Found {len(labels)} labels: {labels}")

        # Extract labels starting with "secret:"
        secret_labels = [label[7:] for label in labels if label.startswith("secret:")]

        if not secret_labels:
            self.logger.info("No 'secret:' labels found in stack labels")
            return []

        self.logger.info(f"Found {len(secret_labels)} secret labels: {secret_labels}")
        return secret_labels

    def _path_to_env_var(self, path: str) -> str:
        """Convert SSM parameter path to environment variable name."""
        # Remove leading slash
        if path.startswith("/"):
            path = path[1:]

        # Replace special characters with underscases and uppercase
        env_var = "TF_VAR_SSM_" + path.replace("/", "_").replace("-", "_").upper()

        # Remove any other special characters
        env_var = "".join(c if c.isalnum() or c == "_" else "_" for c in env_var)

        return env_var

    def _fetch_ssm_parameters(self, paths: List[str]) -> List[Tuple[str, str]]:
        """Fetch parameters from AWS SSM Parameter Store."""
        try:
            ssm_client = boto3.client("ssm", region_name=self.aws_region)
            self.logger.info(f"Connected to AWS SSM in region {self.aws_region}")
        except Exception as e:
            self.logger.error(f"Failed to create SSM client: {e}")
            exit(1)

        parameters = []
        for path in paths:
            try:
                self.logger.debug(f"Fetching parameter: {path}")
                response = ssm_client.get_parameter(Name=path, WithDecryption=True)
                value = response["Parameter"]["Value"]
                env_var = self._path_to_env_var(path)
                parameters.append((env_var, value))
                self.logger.info(f"Successfully fetched {path} -> {env_var}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                if error_code == "ParameterNotFound":
                    self.logger.error(f"Parameter not found: {path}")
                else:
                    self.logger.error(f"AWS error fetching {path}: {e}")
                exit(1)
            except BotoCoreError as e:
                self.logger.error(f"Boto error fetching {path}: {e}")
                exit(1)
            except Exception as e:
                self.logger.error(f"Unexpected error fetching {path}: {e}")
                exit(1)

        return parameters

    def _write_export_script(self, parameters: List[Tuple[str, str]]) -> None:
        """
        Write parameters to a shell script that exports them as environment variables.

        This script will be sourced by hooks to make the variables available.
        """
        export_script_path = "/tmp/ssm_exports.sh"

        try:
            with open(export_script_path, "w") as f:
                f.write("#!/bin/sh\n")
                f.write("# Auto-generated by SSM Parameter Store plugin\n")
                f.write("# This file contains secrets - do not commit or share\n\n")

                for env_var, value in parameters:
                    # Escape single quotes in the value by replacing ' with '\''
                    escaped_value = value.replace("'", "'\\''")
                    f.write(f"export {env_var}='{escaped_value}'\n")

            self.logger.info(
                f"Wrote {len(parameters)} export statements to {export_script_path}"
            )

            # Set restrictive permissions on the file (owner read/write only)
            os.chmod(export_script_path, 0o600)
            self.logger.debug(f"Set permissions on {export_script_path} to 0600")

        except Exception as e:
            self.logger.error(f"Failed to write export script: {e}")
            exit(1)

    def before_init(self) -> None:
        """Fetch SSM parameters before Terraform init."""

        # check if export script already exists
        if os.path.exists("/tmp/ssm_exports.sh"):
            self.logger.info("SSM export script already exists, skipping fetch")
            return

        # Parse labels to get SSM parameter paths
        paths = self._parse_labels()

        if not paths:
            self.logger.info("No SSM parameters to fetch")
            return

        # Fetch parameters from SSM
        self.logger.info(f"Fetching {len(paths)} parameters from AWS SSM")
        parameters = self._fetch_ssm_parameters(paths)

        if not parameters:
            self.logger.warning("No parameters were fetched")
            return

        # Write parameters to export script
        self._write_export_script(parameters)

        self.logger.info("SSM Parameter Store plugin completed successfully")

    def before_plan(self) -> None:
        self.before_init()

    def before_apply(self) -> None:
        self.before_init()

    def before_destroy(self) -> None:
        self.before_init()

    def before_push(self) -> None:
        self.before_init()

    def after_run(self) -> None:
        """Clean up the export script after init phase."""
        export_script_path = "/tmp/ssm_exports.sh"
        try:
            if os.path.exists(export_script_path):
                os.remove(export_script_path)
                self.logger.debug(
                    f"Removed temporary export script: {export_script_path}"
                )
        except Exception as e:
            self.logger.error(f"Failed to remove export script: {e}")
