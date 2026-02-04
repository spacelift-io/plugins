import os
from pathlib import Path

import yaml
from sopsy import Sops, SopsyError

from spaceforge import Binary, Context, Parameter, SpaceforgePlugin, Variable


class SopsPlugin(SpaceforgePlugin):
    """
    This adds the `SOPS` plugin to your Spacelift account.
    It will decrypt an arbitrary number of files based on config you set.

    ## Usage

    1. Spin up the plugin
    2. Add the autoattach label to any stack that has access to your decryption keys.
    3. The secrets you define in your `.sops.yaml` will automatically be decrypted with your configured `creation_rules`.

    #### .sops.yaml

    The `.sops.yaml` file is a configuration file that tells `sops` how to decrypt your files.
    It is a YAML file that contains a list of `creation_rules` that define how to decrypt your files.
    Read more on sops official repository: https://github.com/getsops/sops

    In addition to the sops config, this plugin also uses the `.sops.yaml` file to determine which files to decrypt.
    simply add a list of `secrets` to your `.sops.yaml` in your working directory and the plugin will decrypt them.

    The following `.sops.yaml` example will decrypt a `test_secret.yaml` file using the defined kms key.
    ```yaml
    creation_rules:
      - kms: arn:aws:kms:us-east-2:694182862388:key/6825a259-28df-43be-80f8-6122eb8a5903

    secrets:
      - test_secret.yaml
    ```

    ## Configuration

    Use the "Config File Path" parameter to specify the location of your `.sops.yaml` file.
    This is useful when your stack's `project_root` is set to a subdirectory but the `.sops.yaml`
    file is at the repository root.

    Example: `${TF_VAR_spacelift_workspace_root}/source/.sops.yaml`
    """

    # Plugin metadata
    __plugin_name__ = "Sops"
    __labels__ = ["secrets management", "encryption"]
    __version__ = "1.1.0"
    __author__ = "Spacelift Team"

    __binaries__ = [
        Binary(
            name="sops",
            download_urls={
                "amd64": "https://github.com/getsops/sops/releases/download/v3.9.1/sops-v3.9.1.linux.amd64",
                "arm64": "https://github.com/getsops/sops/releases/download/v3.9.1/sops-v3.9.1.linux.arm64",
            },
        )
    ]

    __parameters__ = [
        Parameter(
            name="Config File Path",
            id="sops_config_path",
            description="Path to the .sops.yaml configuration file. Defaults to .sops.yaml in the working directory. Use an absolute path (e.g., /mnt/workspace/source/.sops.yaml) when the config file is at the repository root but the stack uses a project_root subdirectory.",
            default=".sops.yaml",
            type="string",
            required=False,
        ),
    ]

    __contexts__ = [
        Context(
            name_prefix="sops",
            description="Main context for Sops",
            env=[
                Variable(
                    key="SOPS_CONFIG_PATH",
                    value_from_parameter="sops_config_path",
                ),
            ],
        )
    ]

    def before_init(self):
        # Get config path from environment variable or use default
        config_path = os.environ.get("SOPS_CONFIG_PATH", ".sops.yaml").strip()
        config_file = Path(config_path)

        if not config_file.exists():
            self.logger.error(f"No config file found at: {config_path}")
            return

        secrets = config_file.read_text()
        try:
            secrets = yaml.safe_load(secrets)
        except yaml.YAMLError as e:
            self.logger.error(f"Failed to parse {config_path}: {e}")
            return

        if "secrets" not in secrets:
            self.logger.error(f"No secrets key found in {config_path}.")
            return
        secrets = secrets["secrets"]

        for secret in secrets:
            if not Path(secret).exists():
                self.logger.error(f"Secret file {secret} does not exist.")
                continue

            try:
                self.logger.info(f"Decrypting secret {secret}.")
                sops = Sops(Path(secret), in_place=True)
                sops.decrypt()
                self.logger.info("Decryption successful.")
            except SopsyError as e:
                self.logger.error(f"Failed to decrypt secret: {e}")
            except Exception as e:
                self.logger.error(f"An unexpected error occurred: {e}")
